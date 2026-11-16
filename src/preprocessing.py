"""Preprocessing: parsing, quality flags, cleaning rules, sampling-scope diagnostics and demand tables.

Pipeline (run with `python -m src.preprocessing`):
  1. Parse timestamps and derive quality flags (nothing is dropped).
  2. Apply the cleaning rules: the analysis set excludes orders longer than 24 h; the raw file
     is never modified and every exclusion is logged.
  3. Measure how many couriers are active per day and select the stable experimental window.
  4. Build the forecast table (region_id x aoi_type x day) and the AOI tables used for routing.

Complexity: every vectorised step is O(n) in the number of orders n; building a table over S
series and D days costs O(n + S * D).
"""
import json
from typing import List, Tuple

import numpy as np
import pandas as pd

from . import config
from .data_loader import loadRawDelivery

EARTH_RADIUS_M = 6_371_000.0
DATE = config.DEMAND_DATE_COLUMN


# --------------------------------------------------------------------------------------------
# Parsing and quality flags
# --------------------------------------------------------------------------------------------
def parseMonthDayTime(series: pd.Series, year: int = config.ASSUMED_YEAR) -> pd.Series:
    """Parse 'MM-DD hh:mm:ss' strings to datetime using the given year. O(n)."""
    return pd.to_datetime(f"{year}-" + series, format="%Y-%m-%d %H:%M:%S", errors="coerce")


def haversineMeters(lng1, lat1, lng2, lat2) -> np.ndarray:
    """Vectorised great-circle distance in metres. O(n)."""
    lng1, lat1, lng2, lat2 = map(np.radians, (lng1, lat1, lng2, lat2))
    dLat, dLng = lat2 - lat1, lng2 - lng1
    a = np.sin(dLat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dLng / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))


def addDerivedColumns(df: pd.DataFrame, year: int = config.ASSUMED_YEAR) -> pd.DataFrame:
    """Return a copy with parsed datetimes, duration, calendar fields and quality flags. O(n)."""
    out = df.copy()

    out["accept_dt"] = parseMonthDayTime(out["accept_time"], year)
    out["delivery_dt"] = parseMonthDayTime(out["delivery_time"], year)
    out[DATE] = pd.to_datetime(f"{year}" + out["ds"], format="%Y%m%d", errors="coerce")

    out["delivery_minutes"] = (out["delivery_dt"] - out["accept_dt"]).dt.total_seconds() / 60.0
    out["accept_date"] = out["accept_dt"].dt.normalize()
    out["delivery_date"] = out["delivery_dt"].dt.normalize()
    out["day_of_week"] = out[DATE].dt.dayofweek  # 0 = Monday; depends on ASSUMED_YEAR
    out["is_weekend"] = out["day_of_week"] >= 5
    out["accept_hour"] = out["accept_dt"].dt.hour
    out["delivery_hour"] = out["delivery_dt"].dt.hour

    # Quality flags (True = problem). Nothing is dropped here.
    out["flag_parse_error"] = out[["accept_dt", "delivery_dt", DATE]].isna().any(axis=1)
    out["flag_negative_duration"] = out["delivery_minutes"] < 0
    out["flag_zero_duration"] = out["delivery_minutes"] == 0
    out["flag_missing_accept_gps"] = out[["accept_gps_lng", "accept_gps_lat"]].isna().any(axis=1)
    out["flag_ds_ne_accept_date"] = out[DATE] != out["accept_date"]
    out["flag_ds_ne_delivery_date"] = out[DATE] != out["delivery_date"]
    # GPS fixes at ~(0, 0) are device placeholders, not positions in Jilin (~126.6E, 43.9N).
    nearZero = lambda lng, lat: (lng.abs() < 1) & (lat.abs() < 1)
    out["flag_invalid_gps"] = (nearZero(out["accept_gps_lng"], out["accept_gps_lat"])
                               | nearZero(out["delivery_gps_lng"], out["delivery_gps_lat"]))
    return out


# --------------------------------------------------------------------------------------------
# Cleaning rules
# --------------------------------------------------------------------------------------------
def buildFlaggedAndAnalysis(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Apply the cleaning rules and return (flagged, analysis, exclusionLog).

    Logic:
      (a) GPS fixes at ~(0, 0) are set to NaN, pair-wise.
      (b) Orders longer than MAX_DELIVERY_MINUTES get flag_exclude_over_24h; they leave the
          analysis set but stay in the flagged set and in the exclusion log.
      (c) Rows missing the accept GPS and rows with zero duration are kept (already flagged).
    Complexity: O(n) time, O(n) extra memory.
    """
    flagged = df.copy()
    for prefix in ("accept", "delivery"):
        lngCol, latCol = f"{prefix}_gps_lng", f"{prefix}_gps_lat"
        placeholder = (flagged[lngCol].abs() < 1) & (flagged[latCol].abs() < 1)
        flagged.loc[placeholder, [lngCol, latCol]] = np.nan

    flagged["flag_exclude_over_24h"] = flagged["delivery_minutes"] > config.MAX_DELIVERY_MINUTES
    exclusionLog = (
        flagged.loc[flagged["flag_exclude_over_24h"], ["order_id", "delivery_minutes"]]
        .assign(reason=f"delivery_minutes>{config.MAX_DELIVERY_MINUTES}")
        .reset_index(drop=True)
    )
    analysis = flagged.loc[~flagged["flag_exclude_over_24h"]].reset_index(drop=True)
    return flagged, analysis, exclusionLog


# --------------------------------------------------------------------------------------------
# Sampling-scope diagnostics and experimental window
# --------------------------------------------------------------------------------------------
def dailyActivity(df: pd.DataFrame, dateCol: str = DATE) -> pd.DataFrame:
    """Orders, distinct active couriers and orders per active courier per day.

    Logic: orders = activeCouriers x ordersPerCourier within each day. These observed counts
    describe activity in the sample; they do not identify the cause of a change in demand.
    Complexity: O(n + D) for n orders and D days.
    """
    idx = pd.date_range(df[dateCol].min(), df[dateCol].max(), freq="D")
    daily = df.groupby(dateCol).agg(orders=("order_id", "size"), activeCouriers=("courier_id", "nunique"))
    daily = daily.reindex(idx, fill_value=0)
    daily["ordersPerCourier"] = daily["orders"] / daily["activeCouriers"].replace(0, np.nan)
    daily.index.name = dateCol
    return daily


def decomposeActivityChange(base: pd.DataFrame, comparison: pd.DataFrame) -> dict:
    """Exact log-ratio decomposition of observed mean daily orders. O(D).

    Productivity is total orders / total active courier-days, not the unweighted mean of
    daily ratios. Thus mean orders = mean active couriers * productivity in each period,
    including zero-record days. This accounting identity is descriptive, not causal.
    A period with no orders or activity has no finite log ratio; an unchanged order mean
    has no defined component share.
    """
    def summarize(frame):
        counts = frame[["orders", "activeCouriers"]]
        if (counts.empty or not np.isfinite(counts.to_numpy(dtype=float)).all()
                or (counts < 0).any().any()
                or ((counts.orders > 0) & (counts.activeCouriers == 0)).any()):
            raise ValueError("Expected nonnegative finite daily counts and couriers for every order.")
        totals = counts.sum()
        if totals.orders <= 0 or totals.activeCouriers <= 0:
            raise ValueError("Each period must have positive total orders and active courier-days.")
        return dict(orders_per_day=float(totals.orders / len(counts)),
                    couriers_per_day=float(totals.activeCouriers / len(counts)),
                    orders_per_courier_day=float(totals.orders / totals.activeCouriers))

    before, after = summarize(base), summarize(comparison)
    orderChange = float(np.log(before["orders_per_day"] / after["orders_per_day"]))
    courierChange = float(np.log(before["couriers_per_day"] / after["couriers_per_day"]))
    productivityChange = float(np.log(before["orders_per_courier_day"] / after["orders_per_courier_day"]))
    return dict(base=before, comparison=after, order_log_ratio=orderChange,
                courier_log_ratio=courierChange, productivity_log_ratio=productivityChange,
                courier_log_share=(courierChange / orderChange if not np.isclose(orderChange, 0) else None))


def _bestSplit(cum: np.ndarray, cum2: np.ndarray, lo: int, hi: int, minSegment: int) -> Tuple[int, float]:
    """Best single split of [lo, hi) by SSE reduction using prefix sums. O(hi - lo)."""
    ks = np.arange(lo + minSegment, hi - minSegment + 1)
    if len(ks) == 0:
        return -1, 0.0
    total, total2 = cum[hi] - cum[lo], cum2[hi] - cum2[lo]
    sseAll = total2 - total ** 2 / (hi - lo)
    nl, nr = ks - lo, hi - ks
    sl, sl2 = cum[ks] - cum[lo], cum2[ks] - cum2[lo]
    sr, sr2 = total - sl, total2 - sl2
    gains = sseAll - ((sl2 - sl ** 2 / nl) + (sr2 - sr ** 2 / nr))
    best = int(np.argmax(gains))
    return int(ks[best]), float(gains[best])


def findMeanShifts(values, maxBreaks: int = 6, minSegment: int = 7, minGainFrac: float = 0.02) -> List[int]:
    """Greedy binary segmentation for mean shifts; returns sorted start indices of new segments.

    Stops when maxBreaks is reached or the best gain is below minGainFrac of the total SSE.
    Complexity: O(B x n) for B breaks (each new segment pair is scanned once).
    """
    x = np.asarray(values, dtype=float)
    cum, cum2 = np.concatenate([[0], np.cumsum(x)]), np.concatenate([[0], np.cumsum(x ** 2)])
    totalSse = cum2[-1] - cum[-1] ** 2 / len(x)
    segments = [(0, len(x))]
    cache = {segments[0]: _bestSplit(cum, cum2, 0, len(x), minSegment)}
    breaks: List[int] = []
    while len(breaks) < maxBreaks:
        seg = max(segments, key=lambda s: cache[s][1])
        k, gain = cache[seg]
        if k < 0 or totalSse <= 0 or gain < minGainFrac * totalSse:
            break
        breaks.append(k)
        segments.remove(seg)
        for child in ((seg[0], k), (k, seg[1])):
            segments.append(child)
            cache[child] = _bestSplit(cum, cum2, child[0], child[1], minSegment)
    return sorted(breaks)


def timeSplit(index: pd.DatetimeIndex, trainShare: float = 0.6, validationShare: float = 0.2) -> dict:
    """Chronological train/validation/test bounds (inclusive dates) for a day index. O(1)."""
    n = len(index)
    a, b = int(n * trainShare), int(n * (trainShare + validationShare))
    return {"train": [str(index[0].date()), str(index[a - 1].date())],
            "validation": [str(index[a].date()), str(index[b - 1].date())],
            "test": [str(index[b].date()), str(index[-1].date())]}


def segmentDaily(daily: pd.DataFrame, breaks: List[int]) -> List[Tuple[int, int]]:
    """(start, end) positions of the segments delimited by the break positions. O(B)."""
    edges = [0] + list(breaks) + [len(daily)]
    return list(zip(edges[:-1], edges[1:]))


def selectStableWindow(daily: pd.DataFrame, maxBreaks: int = 5, minSegment: int = 7) -> dict:
    """Select the experimental window and the chronological splits.

    Logic: the window is the longest constant-mean segment of the daily active-courier count.
    Two scenarios are defined: the primary stable window and the full period (sensitivity).
    Complexity: O(B x D) for D days.
    """
    breaks = findMeanShifts(daily["activeCouriers"].values, maxBreaks=maxBreaks, minSegment=minSegment)
    start, end = max(segmentDaily(daily, breaks), key=lambda s: s[1] - s[0])
    stableIdx = daily.index[start:end]
    return {
        "method": "longest mean-shift segment of daily active couriers",
        "break_dates": [str(daily.index[k].date()) for k in breaks],
        "start": str(stableIdx[0].date()), "end": str(stableIdx[-1].date()), "days": len(stableIdx),
        "splits": {"primary_stable_period": timeSplit(stableIdx),
                   "sensitivity_full_period": timeSplit(daily.index)},
    }


# --------------------------------------------------------------------------------------------
# Demand tables
# --------------------------------------------------------------------------------------------
def completePanel(df: pd.DataFrame, keys: List[str]) -> pd.DataFrame:
    """Expand the observed keys across the calendar and flag cells that are filled with zero.

    A day with no order in the whole city is not observed: city_observed is False and the zero
    does not establish zero underlying demand. Complexity: O(n + S * D).
    """
    if df[keys + [DATE]].isna().any().any():
        raise ValueError("Missing aggregation keys or date; resolve before counting.")
    days = pd.DataFrame({DATE: pd.date_range(df[DATE].min(), df[DATE].max())})
    grid = df[keys].drop_duplicates().merge(days, how="cross")
    counts = df.groupby(keys + [DATE]).size().rename("demand").reset_index()
    panel = grid.merge(counts, on=keys + [DATE], how="left", validate="one_to_one")
    panel["demand"] = panel["demand"].fillna(0).astype("int64")
    panel["city_observed"] = panel[DATE].isin(df[DATE].unique())
    panel["zero_assumed"] = panel["demand"].eq(0)
    assert panel["demand"].sum() == len(df), "order count is not conserved"
    return panel.sort_values(keys + [DATE]).reset_index(drop=True)


def buildDemandPanel(df: pd.DataFrame, stable=None) -> pd.DataFrame:
    """One row per region_id x aoi_type x day; structural zeros stay explicit. O(n + S * D)."""
    panel = completePanel(df, ["region_id", "aoi_type"])
    panel["series_id"] = "r" + panel.region_id.astype(str) + "_t" + panel.aoi_type.astype(str)
    panel["day_of_week"] = panel[DATE].dt.dayofweek
    panel["is_weekend"] = panel.day_of_week >= 5
    if stable:
        panel["in_stable_period"] = panel[DATE].between(*stable)
    return panel.sort_values(["series_id", DATE]).reset_index(drop=True)


def buildAoiLookup(df: pd.DataFrame) -> pd.DataFrame:
    """AOI attributes: modal region and type, median location, ambiguity flag. O(n log n)."""
    grp = df.groupby("aoi_id")
    lookup = grp.agg(n_orders=("order_id", "size"), n_regions=("region_id", "nunique"),
                     n_types=("aoi_type", "nunique"), lng=("lng", "median"), lat=("lat", "median"))
    for col in ["region_id", "aoi_type"]:
        lookup[col] = grp[col].agg(lambda s: s.mode().iloc[0])
    lookup["ambiguous_region"] = lookup.n_regions > 1
    return lookup.reset_index()


def buildAoiTables(df: pd.DataFrame, lookup: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """AOI x day table and the exact AOI x region x type x day breakdown. O(n + A * D).

    The breakdown keeps the observed region of every order, so the orders of an AOI that appears
    in several regions are never moved to its modal region.
    """
    aoiPanel = completePanel(df, ["aoi_id"]).merge(
        lookup[["aoi_id", "region_id", "aoi_type", "lng", "lat", "ambiguous_region"]],
        on="aoi_id", validate="many_to_one")
    detail = (df.groupby(["aoi_id", "region_id", "aoi_type", DATE]).size()
              .rename("demand").reset_index())
    return aoiPanel, detail


def auditTables(df: pd.DataFrame, panel: pd.DataFrame, aoiPanel: pd.DataFrame,
                detail: pd.DataFrame, lookup: pd.DataFrame) -> dict:
    """Check that every table conserves the daily order counts and summarise the panel. O(n)."""
    expected = df.groupby(DATE).size()
    for frame in (panel, aoiPanel, detail):
        actual = frame.groupby(DATE).demand.sum().reindex(expected.index)
        assert actual.equals(expected), "daily order counts differ between tables"
    unobserved = panel.loc[~panel.city_observed, DATE].dt.strftime("%Y-%m-%d").unique().tolist()
    return dict(orders=len(df), forecast_series=int(panel.series_id.nunique()), aois=len(lookup),
                days=int(panel[DATE].nunique()), forecast_rows=len(panel), aoi_rows=len(aoiPanel),
                ambiguous_aois=int(lookup.ambiguous_region.sum()), unobserved_city_days=sorted(unobserved))


def compareAggregation(panel: pd.DataFrame, aoiPanel: pd.DataFrame, window: Tuple[str, str]) -> pd.DataFrame:
    """Zero-cell share of the two aggregation levels over the full period and the window. O(rows)."""
    rows = []
    for name, frame in (("region_type", panel), ("aoi", aoiPanel)):
        for period, sub in (("full", frame), ("stable", frame[frame[DATE].between(*window)])):
            rows.append(dict(level=name, period=period, rows=len(sub),
                             zero_share=float(sub.demand.eq(0).mean()), orders=int(sub.demand.sum())))
    return pd.DataFrame(rows)


def main() -> None:
    """Write every processed table from the raw file. O(n + S * D + A * D)."""
    raw = loadRawDelivery()
    assert (raw["city"] == config.EXPECTED_CITY).all(), "unexpected city in the raw file"
    flagged, analysis, exclusionLog = buildFlaggedAndAnalysis(addDerivedColumns(raw))
    assert flagged.order_id.is_unique and len(flagged) == len(analysis) + len(exclusionLog)

    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    flagged.to_parquet(config.FLAGGED_FILE, index=False)
    analysis.to_parquet(config.ANALYSIS_FILE, index=False)
    exclusionLog.to_csv(config.EXCLUDED_LOG_FILE, index=False)

    window = selectStableWindow(dailyActivity(analysis))
    config.STABLE_PERIOD_FILE.write_text(json.dumps(window, indent=2), encoding="utf-8")

    panel = buildDemandPanel(analysis, (window["start"], window["end"]))
    lookup = buildAoiLookup(analysis)
    aoiPanel, detail = buildAoiTables(analysis, lookup)
    audit = auditTables(analysis, panel, aoiPanel, detail, lookup)

    panel.to_csv(config.DEMAND_PANEL_FILE, index=False)
    aoiPanel.to_parquet(config.AOI_DAILY_FILE, index=False)
    detail.to_csv(config.AOI_REGION_DAILY_FILE, index=False)
    lookup.to_csv(config.AOI_LOOKUP_FILE, index=False)
    compareAggregation(panel, aoiPanel, (window["start"], window["end"])).to_csv(config.AGGREGATION_FILE, index=False)
    config.PANEL_AUDIT_FILE.write_text(json.dumps(audit, indent=2), encoding="utf-8")

    # Lookups estimated on the training orders of each scenario, for the routing stage.
    for scenario, bounds in window["splits"].items():
        trainOrders = analysis[analysis[DATE].between(*bounds["train"])]
        buildAoiLookup(trainOrders).to_csv(config.trainAoiLookupFile(scenario), index=False)

    print(f"raw={len(raw):,} analysis={len(analysis):,} excluded={len(exclusionLog)} "
          f"series={audit['forecast_series']} aois={audit['aois']} window={window['start']}..{window['end']}")


if __name__ == "__main__":
    main()

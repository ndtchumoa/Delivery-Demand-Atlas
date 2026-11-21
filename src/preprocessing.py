"""Date parsing and calendar completion for observed delivery orders."""
import pandas as pd

from . import config

DATE = config.DEMAND_DATE_COLUMN


def parseMonthDayTime(series: pd.Series, year: int = config.ASSUMED_YEAR) -> pd.Series:
    """Parse 'MM-DD hh:mm:ss' strings to datetime using the given year."""
    return pd.to_datetime(f"{year}-" + series, format="%Y-%m-%d %H:%M:%S", errors="coerce")


def addDerivedColumns(df: pd.DataFrame, year: int = config.ASSUMED_YEAR) -> pd.DataFrame:
    """Return a copy with parsed datetimes, duration, calendar fields and quality flags."""
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


def completePanel(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Expand the observed keys across the calendar and flag cells that are filled with zero.

    Callers can use city_observed to mask days with no orders anywhere in the city.
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

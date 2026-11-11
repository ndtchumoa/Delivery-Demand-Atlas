"""One-day-ahead features built from the demand panel without using the target day or later.

Logic: for every series, observed demand is shifted before any rolling statistic is computed, so
the features of day t use information up to day t-1 only. A day with no order in the whole city is
unobserved: it is kept as NaN (never replaced by zero) in lags and rolling windows and it is not a
valid label. Features are built inside the scenario window only, so no history from before the
window is used; the first WARMUP_DAYS days of the window serve as history.

Complexity: O(N log N) for N panel rows (sorting plus grouped shifts and rolling windows).
"""
import pandas as pd

from . import config

DATE = config.DEMAND_DATE_COLUMN


def buildFeatures(panel: pd.DataFrame) -> pd.DataFrame:
    """Lag, rolling and calendar features per series. O(N log N)."""
    out = panel.sort_values(["series_id", DATE]).copy()
    out["observed_demand"] = out.demand.where(out.city_observed)
    group = out.groupby("series_id").observed_demand
    for lag in config.LAGS:
        out[f"lag_{lag}"] = group.shift(lag)
    for window in config.ROLLING_WINDOWS:
        out[f"rolling_mean_{window}"] = group.transform(
            lambda s: s.shift(1).rolling(window, min_periods=window).mean())
        out[f"rolling_std_{window}"] = group.transform(
            lambda s: s.shift(1).rolling(window, min_periods=window).std(ddof=0))
    out["day_of_month"] = out[DATE].dt.day
    out["month"] = out[DATE].dt.month
    required = [f"lag_{lag}" for lag in config.LAGS] + [f"rolling_mean_{max(config.ROLLING_WINDOWS)}"]
    out["history_ready"] = out[required].notna().all(axis=1)
    return out


def buildScenarioFeatures(panel: pd.DataFrame, bounds: dict) -> pd.DataFrame:
    """Features inside one scenario window, with a `split` column (train/validation/test). O(N log N)."""
    window = panel[panel[DATE].between(bounds["train"][0], bounds["test"][1])]
    data = buildFeatures(window)
    data["split"] = "unused"
    for split, (start, end) in bounds.items():
        data.loc[data[DATE].between(start, end), "split"] = split
    return data


def evaluationCells(data: pd.DataFrame) -> pd.DataFrame:
    """Validation and test cells that are observed and have the full feature history. O(N)."""
    mask = data.split.isin(["validation", "test"]) & data.city_observed & data.history_ready
    return data[mask]

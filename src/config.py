"""Central configuration: paths, modelling conventions and reference statistics."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"
FORECASTS_DIR = PROJECT_ROOT / "outputs" / "forecasts"

RAW_FILE_NAME = "delivery_jl.csv"
EXPECTED_CITY = "Jilin"

# Year convention. Raw timestamps are "MM-DD hh:mm:ss" without a year. The LaDe datasheet only
# states that the data was extracted "between May and November of a recent year", which is
# consistent with the observed span (12 May - 28 Oct) but does not give the year. 2022 is a
# technical convention: weekday and weekend features derived from it are assumption-dependent
# and must not be reported as verified calendar effects.
ASSUMED_YEAR = 2022

# Demand-date convention. `ds` equals the ACCEPT date in every row, so the target counts orders
# received (assigned) per day, not orders completed per day.
DEMAND_DATE_COLUMN = "ds_date"

# Cleaning rules. Orders longer than this are excluded from the analysis set only; the raw file
# is never modified and every exclusion is logged.
MAX_DELIVERY_MINUTES = 24 * 60
FAR_STOP_KM = 20  # informational distance used in the EDA, not a filter

# Feature design (lags and rolling windows are in days; rolling windows are shifted by one day).
LAGS = (1, 7, 14)
ROLLING_WINDOWS = (7, 14)
WARMUP_DAYS = 14

# Processed tables
FLAGGED_FILE = PROCESSED_DIR / "delivery_jl_flagged.parquet"        # all rows + quality flags
ANALYSIS_FILE = PROCESSED_DIR / "delivery_jl_analysis.parquet"      # exclusion rules applied
EXCLUDED_LOG_FILE = PROCESSED_DIR / "excluded_rows.csv"
DEMAND_PANEL_FILE = PROCESSED_DIR / "demand_panel.csv"              # region_id x aoi_type x day
AOI_DAILY_FILE = PROCESSED_DIR / "aoi_daily.parquet"                # aoi_id x day (descriptive region label)
AOI_REGION_DAILY_FILE = PROCESSED_DIR / "aoi_region_daily.csv"      # aoi_id x region x type x day, exact
AOI_LOOKUP_FILE = PROCESSED_DIR / "aoi_lookup.csv"                  # full-period lookup, descriptive only
STABLE_PERIOD_FILE = PROCESSED_DIR / "stable_period.json"
PANEL_AUDIT_FILE = PROCESSED_DIR / "panel_audit.json"
AGGREGATION_FILE = PROCESSED_DIR / "aggregation_comparison.csv"


def featuresFile(scenario: str) -> Path:
    """Feature table of a scenario (primary_stable_period or sensitivity_full_period)."""
    return PROCESSED_DIR / f"features_{scenario}.parquet"


def trainAoiLookupFile(scenario: str) -> Path:
    """AOI lookup estimated on the training orders of a scenario only."""
    return PROCESSED_DIR / f"aoi_lookup_train_{scenario}.csv"


# Forecast outputs
BASELINE_PREDICTIONS_FILE = FORECASTS_DIR / "baseline_predictions.csv"
BASELINE_METRICS_FILE = FORECASTS_DIR / "baseline_metrics.csv"
BASELINE_PROTOCOL_FILE = FORECASTS_DIR / "baseline_protocol.json"

# Reference statistics for Jilin, LaDe-D (Wu et al., arXiv:2306.10675v3, Table 12).
PAPER_JILIN_STATS = {
    "couriers": 57,
    "packages": 31_000,  # reported as "31k" (rounded)
    "avgEtaMinutes": 203,
    "avgPackagePerCourierDay": 16.2,
}

# Routing preparation policy from outline v4. Accept-GPS centres are descriptive only.
# Actual depot coordinates and F/Q are not fitted yet; freeze them after validation.
ROUTING_DEPOT_POLICY = "single_common_depot_from_training_aoi_demand"

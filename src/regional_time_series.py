"""Build the daily regional demand panel and compare the observed time series."""
import argparse
from itertools import combinations
from pathlib import Path

import pandas as pd

from . import config
from .data_loader import loadRawDelivery
from .preprocessing import completePanel, validateDemandOrders

DATE = config.DEMAND_DATE_COLUMN
OUTPUT_DIR = config.PROJECT_ROOT / "outputs" / "analysis"
# Historical stable window from the forecast experiment, used for sensitivity only.
STABLE_PERIOD = (f"{config.ASSUMED_YEAR}-06-27", f"{config.ASSUMED_YEAR}-10-02")


def buildRegionalPanel(raw: pd.DataFrame) -> pd.DataFrame:
    orders = validateDemandOrders(raw)
    panel = completePanel(orders, ["region_id"])
    panel["demand"] = panel["demand"].where(panel["city_observed"]).astype("Int64")
    return panel[["region_id", DATE, "demand", "city_observed"]]


def summarizeRegions(panel: pd.DataFrame) -> pd.DataFrame:
    observed = panel.loc[panel["city_observed"]]
    return observed.assign(is_zero=observed["demand"].eq(0)).groupby("region_id", as_index=False).agg(
        observed_days=("demand", "count"),
        orders=("demand", "sum"),
        daily_mean=("demand", "mean"),
        daily_median=("demand", "median"),
        daily_std=("demand", "std"),
        zero_days=("is_zero", "sum"),
    )


def compareRegions(panel: pd.DataFrame) -> pd.DataFrame:
    daily = panel.pivot(index=DATE, columns="region_id", values="demand").sort_index()
    calendar = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    daily = daily.reindex(calendar).astype("float64")

    results = []
    for transform, values in (("level", daily), ("daily_change", daily.diff())):
        for first, second in combinations(values.columns, 2):
            paired = values[[first, second]].dropna()
            coefficient = float("nan")
            if len(paired) >= 2 and paired[first].nunique() > 1 and paired[second].nunique() > 1:
                coefficient = paired[first].corr(paired[second])
            results.append({
                "transform": transform,
                "region_a": first,
                "region_b": second,
                "paired_days": len(paired),
                "pearson_r": coefficient,
            })
    return pd.DataFrame(results, columns=[
        "transform", "region_a", "region_b", "paired_days", "pearson_r",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Path to the raw Jilin CSV.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    panel = buildRegionalPanel(loadRawDelivery(args.input))
    stable = panel.loc[panel[DATE].between(*STABLE_PERIOD)]
    comparisons = pd.concat(
        [compareRegions(frame).assign(period=period)
         for period, frame in (("full", panel), ("stable", stable)) if not frame.empty],
        ignore_index=True,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    options = {"index": False, "lineterminator": "\n", "float_format": "%.6f"}
    panel.to_csv(args.output_dir / "regional_daily_demand.csv", **options)
    summarizeRegions(panel).to_csv(args.output_dir / "regional_summary.csv", **options)
    comparisons.to_csv(args.output_dir / "regional_correlations.csv", **options)


if __name__ == "__main__":
    main()

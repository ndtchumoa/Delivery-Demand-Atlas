"""Baseline forecasters for the one-day-ahead demand of every region_id x aoi_type series.

Logic: the historical mean and the historical same-weekday mean are fitted once on the training
split and kept fixed. The lag and rolling baselines use the observed past only and are updated
every day (rolling one-day-ahead). All baselines are scored on exactly the same cells.
Run with `python -m src.train_forecast`.

Complexity: O(N log N) per scenario for N panel rows.
"""
import json

import pandas as pd

from . import config
from .data_loader import loadDemandPanel
from .features import buildScenarioFeatures, evaluationCells

DATE = config.DEMAND_DATE_COLUMN
BASELINES = ["naive_1", "seasonal_7", "rolling_mean_7", "rolling_mean_14", "historical_mean", "historical_weekday"]
PREDICTION_COLUMNS = ["series_id", "region_id", "aoi_type", DATE, "split", "demand"]


def fitHistoricalBaselines(data: pd.DataFrame) -> pd.DataFrame:
    """Add the baseline columns; historical means are fitted on the observed training days. O(N)."""
    train = data[(data.split == "train") & data.city_observed]
    means = train.groupby("series_id").demand.mean()
    weekdayMeans = train.groupby(["series_id", "day_of_week"]).demand.mean().rename("historical_weekday")
    out = data.merge(weekdayMeans, on=["series_id", "day_of_week"], how="left", validate="many_to_one")
    out["historical_mean"] = out.series_id.map(means).fillna(0)
    out["historical_weekday"] = out.historical_weekday.fillna(out.historical_mean)
    out["naive_1"] = out.lag_1
    out["seasonal_7"] = out.lag_7
    return out


def predictBaselines(data: pd.DataFrame, scenario: str) -> pd.DataFrame:
    """Long table of baseline predictions on the evaluation cells; negatives are clipped to 0. O(N)."""
    cells = evaluationCells(data)
    assert cells[BASELINES].notna().all().all(), "baselines must be defined on every evaluation cell"
    frames = []
    for model in BASELINES:
        pred = cells[PREDICTION_COLUMNS].copy()
        pred["prediction"], pred["model"], pred["scenario"] = cells[model].clip(lower=0), model, scenario
        frames.append(pred)
    return pd.concat(frames, ignore_index=True)


def runScenario(panel: pd.DataFrame, scenario: str, bounds: dict):
    """Features with fitted baselines and the baseline predictions of one scenario. O(N log N)."""
    data = fitHistoricalBaselines(buildScenarioFeatures(panel, bounds))
    return data, predictBaselines(data, scenario)


def main() -> None:
    """Run the primary window and the full-period sensitivity scenario and save the outputs."""
    panel = loadDemandPanel()
    window = json.loads(config.STABLE_PERIOD_FILE.read_text())
    predictions = []
    for scenario, bounds in window["splits"].items():
        data, pred = runScenario(panel, scenario, bounds)
        data.to_parquet(config.featuresFile(scenario), index=False)
        predictions.append(pred)
    config.FORECASTS_DIR.mkdir(parents=True, exist_ok=True)
    pd.concat(predictions, ignore_index=True).to_csv(config.BASELINE_PREDICTIONS_FILE, index=False)
    print(f"baseline predictions: {sum(len(p) for p in predictions):,} rows")


if __name__ == "__main__":
    main()

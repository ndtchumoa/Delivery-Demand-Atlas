"""Forecast evaluation: MAE, RMSE and WAPE at series level and after summing by region.

Logic: WAPE is the pooled ratio (sum of absolute errors) / (sum of actual demand), not an average
of per-cell percentages, so that cells with zero demand do not distort it. The model is chosen on
the validation split only; the test split is never used for selection.
Run with `python -m src.evaluate_forecast`.

Complexity: O(N) per model and level for N scored cells.
"""
import json
from typing import List

import numpy as np
import pandas as pd

from . import config
from .features import evaluationCells

DATE = config.DEMAND_DATE_COLUMN


def scoreForecast(actual, predicted) -> dict:
    """MAE, RMSE and pooled WAPE; WAPE is NaN when total demand is zero. O(N)."""
    actual, predicted = np.asarray(actual, float), np.asarray(predicted, float)
    error = predicted - actual
    total = actual.sum()
    return dict(mae=float(np.abs(error).mean()), rmse=float(np.sqrt((error ** 2).mean())),
                wape=float(np.abs(error).sum() / total) if total else float("nan"),
                rows=len(actual), actual_orders=float(total))


def evaluatePredictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Metrics per scenario, model, split and level (series, or region after summing). O(N)."""
    rows: List[dict] = []
    for (scenario, model), pred in predictions.groupby(["scenario", "model"], sort=False):
        for split, sub in pred.groupby("split"):
            for level in ("series", "region"):
                frame = sub if level == "series" else (
                    sub.groupby(["region_id", DATE])[["demand", "prediction"]].sum().reset_index())
                rows.append(dict(scenario=scenario, split=split, level=level, model=model,
                                 **scoreForecast(frame.demand, frame.prediction)))
    return pd.DataFrame(rows)


def selectOnValidation(metrics: pd.DataFrame, scenario: str) -> str:
    """Model with the lowest series-level validation WAPE (ties broken by MAE, then name). O(M log M)."""
    sub = metrics[(metrics.scenario == scenario) & (metrics.split == "validation") & (metrics.level == "series")]
    return sub.sort_values(["wape", "mae", "model"]).iloc[0].model


def summarizeProtocol(data: pd.DataFrame, scenario: str, bounds: dict, selected: str) -> dict:
    """Evaluation protocol of one scenario: splits, eligible days and excluded dates. O(N)."""
    cells = evaluationCells(data)
    ready = data[(data.split == "train") & data.history_ready & data.city_observed]
    evalSplits = data.split.isin(["validation", "test"])
    excluded = data.loc[evalSplits & (~data.city_observed | ~data.history_ready), DATE]
    return dict(scenario=scenario, splits=bounds, selected_on_validation=selected, warmup_days=config.WARMUP_DAYS,
                history_policy="within scenario only; observed t-1 available for rolling one-day forecasts",
                ready_train_rows=int(len(ready)), ready_train_days=int(ready[DATE].nunique()),
                scored_days={s: int(cells.loc[cells.split == s, DATE].nunique()) for s in ("validation", "test")},
                excluded_eval_days=sorted(excluded.dt.strftime("%Y-%m-%d").unique().tolist()))


def main() -> None:
    """Score the saved baseline predictions and write metrics and protocol files."""
    window = json.loads(config.STABLE_PERIOD_FILE.read_text(encoding="utf-8"))
    predictions = pd.read_csv(config.BASELINE_PREDICTIONS_FILE, parse_dates=[DATE])
    metrics = evaluatePredictions(predictions)
    protocol = []
    for scenario, bounds in window["splits"].items():
        data = pd.read_parquet(config.featuresFile(scenario))
        protocol.append(summarizeProtocol(data, scenario, bounds, selectOnValidation(metrics, scenario)))
    metrics.to_csv(config.BASELINE_METRICS_FILE, index=False)
    config.BASELINE_PROTOCOL_FILE.write_text(json.dumps(protocol, indent=2), encoding="utf-8")
    best = metrics[(metrics.scenario == "primary_stable_period") & (metrics.split == "test") & (metrics.level == "series")]
    print(best.sort_values("wape")[["model", "mae", "rmse", "wape"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()


"""Build the offline Jilin forecast demo from the saved primary-window experiment."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .data_loader import loadDemandPanel
from .evaluate_forecast import evaluatePredictions
from .train_forecast import runScenario

SCENARIO = "primary_stable_period"
MODELS = ["rolling_mean_7", "lightgbm_full", "xgboost_full"]
DATE = config.DEMAND_DATE_COLUMN
KEYS = ["split", DATE, "region_id", "aoi_type", "series_id"]
TEMPLATE = config.PROJECT_ROOT / "demo" / "forecast_template.html"
OUTPUT_DIR = config.FORECASTS_DIR / "demo"


def verifyMetrics(actual, expected):
    keys = ["split", "level", "model"]
    columns = ["mae", "rmse", "wape", "rows", "actual_orders"]
    left = actual.set_index(keys).sort_index()
    right = expected.set_index(keys).sort_index().reindex(left.index)
    np.testing.assert_allclose(left[columns], right[columns], atol=1e-10, rtol=1e-10)


def buildDemo(output=OUTPUT_DIR):
    windows = json.loads(config.STABLE_PERIOD_FILE.read_text(encoding="utf-8"))["splits"]
    bounds = windows[SCENARIO]
    _, baselines = runScenario(loadDemandPanel(), SCENARIO, bounds)
    rolling = baselines.loc[baselines.model.eq(MODELS[0])].astype({DATE: "datetime64[us]"})

    saved = config.FORECASTS_DIR / "ml_validation" / SCENARIO
    validation = pd.read_csv(saved / "validation_predictions.csv", parse_dates=[DATE])
    validation = validation.loc[validation.scenario.eq(SCENARIO) & validation.split.eq("validation")]
    validation = validation.astype({DATE: "datetime64[us]"})
    reference = rolling.loc[rolling.split.eq("validation")].sort_values(KEYS).reset_index(drop=True)
    if reference.empty or not rolling.split.eq("test").any():
        raise ValueError("The baseline must contain primary validation and test predictions.")
    for model in MODELS:
        candidate = validation.loc[validation.model.eq(model)].sort_values(KEYS).reset_index(drop=True)
        pd.testing.assert_frame_equal(reference[KEYS + ["demand"]], candidate[KEYS + ["demand"]])
        if model == MODELS[0]:
            np.testing.assert_allclose(reference.prediction, candidate.prediction, rtol=1e-12, atol=1e-12)

    predictions = pd.concat([rolling, validation.loc[validation.model.isin(MODELS[1:])]], ignore_index=True)
    if predictions.duplicated(KEYS + ["model"]).any():
        raise ValueError("The demo input contains duplicate model predictions.")
    if not np.isfinite(predictions.prediction).all() or predictions.prediction.lt(0).any():
        raise ValueError("The demo requires finite, nonnegative predictions.")
    metrics = evaluatePredictions(predictions)
    validationMetrics = pd.read_csv(saved / "validation_metrics.csv")
    baselineMetrics = pd.read_csv(config.BASELINE_METRICS_FILE)
    verifyMetrics(metrics.loc[metrics.split.eq("validation")], validationMetrics)
    verifyMetrics(metrics.loc[metrics.split.eq("test")], baselineMetrics.loc[baselineMetrics.scenario.eq(SCENARIO)])

    wide = predictions.pivot(index=KEYS + ["demand"], columns="model", values="prediction").reset_index()
    wide = wide[KEYS + ["demand", *MODELS]]
    wide[DATE] = wide[DATE].dt.strftime("%Y-%m-%d")
    wide.columns.name = None
    csv = wide.to_csv(index=False, lineterminator="\n", float_format="%.12g")
    data = dict(bounds=bounds, models=MODELS, rows=json.loads(wide.to_json(orient="values", double_precision=12)),
                metrics=metrics.to_dict("records"), csv=csv)
    template = TEMPLATE.read_text(encoding="utf-8")
    placeholder = "__FORECAST_PAYLOAD__"
    if template.count(placeholder) != 1:
        raise ValueError("The demo template must contain exactly one data placeholder.")
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")

    output.mkdir(parents=True, exist_ok=True)
    (output / "Demo_Du_bao_Jilin.html").write_text(template.replace(placeholder, payload), encoding="utf-8", newline="\n")
    (output / "Du_bao_Jilin.csv").write_text(csv, encoding="utf-8", newline="\n")
    metrics.to_csv(output / "Chi_so_Du_bao_Jilin.csv", index=False, encoding="utf-8", lineterminator="\n",
                   float_format="%.12g")
    print(metrics.loc[metrics.level.eq("series")].to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    buildDemo(parser.parse_args().output_dir)

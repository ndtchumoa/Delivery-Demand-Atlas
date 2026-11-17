"""Train pooled LightGBM/XGBoost models and ablations; validation only in this phase.

Run: python -m src.train_ml [--scenario primary_stable_period|sensitivity_full_period|all]
No test scoring switch is exposed until the experiment protocol is reviewed.
"""
import argparse
import hashlib
import importlib.metadata
import itertools
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd

from . import config
from .data_loader import loadAnalysisOrders, loadDemandPanel
from .evaluate_forecast import evaluatePredictions, scoreForecast, selectOnValidation
from .feature_schema import featureColumns
from .features import buildScenarioFeatures
from .spatial_features import buildSpatialFeatures
from .train_forecast import runScenario, PREDICTION_COLUMNS

DATE = config.DEMAND_DATE_COLUMN
SPEC_FILE = config.PROJECT_ROOT / 'configs/ml_experiment.json'


def writeJson(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def encodeFeatures(train, other, columns, categorical):
    """One-hot vocabulary fitted on train only; unknown categories encode as all zero."""
    vocabulary = {c: sorted(train[c].dropna().unique().tolist()) for c in categorical if c in columns}

    def transform(frame):
        result = pd.DataFrame(index=frame.index)
        for col in columns:
            if col in vocabulary:
                for i, value in enumerate(vocabulary[col]):
                    result[f'{col}__{i}'] = frame[col].eq(value).astype(float)
            else:
                result[col] = pd.to_numeric(frame[col]).astype(float)
        if not np.isfinite(result.to_numpy()).all():
            raise ValueError('Non-finite ML inputs')
        return result

    return transform(train), transform(other), vocabulary


def candidateGrid(spec, family):
    grid = spec[family]
    for values in itertools.product(*grid.values()):
        yield dict(zip(grid, values))


def makeModel(family, params, spec):
    common = dict(learning_rate=spec['learning_rate'], random_state=spec['seed'], n_jobs=spec['n_jobs'], **params)
    if family == 'lightgbm':
        from lightgbm import LGBMRegressor
        return LGBMRegressor(objective='regression', deterministic=True, force_col_wise=True,
                             verbosity=-1, reg_lambda=1.0, **common)
    from xgboost import XGBRegressor
    return XGBRegressor(objective='reg:squarederror', tree_method='hist', reg_lambda=1.0, **common)


def fitVariant(data, family, excluded, spec, schema, output):
    """Select only on validation; persist selected native model and train-only encoding metadata."""
    train = data[data.split == 'train']
    validation = data[data.split == 'validation']
    if train.empty or validation.empty:
        raise ValueError('Empty eligible training or validation set')
    columns = featureColumns(excluded)
    xTrain, xVal, vocabulary = encodeFeatures(train, validation, columns, schema['categorical'])
    variant = family + ('_without_' + excluded[0] if excluded else '_full')
    trials, best = [], None
    for i, params in enumerate(candidateGrid(spec, family)):
        model = makeModel(family, params, spec)
        model.fit(xTrain, train.demand)
        prediction = np.maximum(model.predict(xVal), 0)
        metrics = scoreForecast(validation.demand, prediction)
        if not np.isfinite(prediction).all() or not np.isfinite(metrics['wape']):
            raise ValueError('Invalid predictions or zero total validation demand')
        candidate = f'{variant}_{i:02d}'
        trials.append(dict(variant=variant, candidate=candidate, parameters=json.dumps(params, sort_keys=True), **metrics))
        key = (metrics['wape'], metrics['mae'], candidate)
        if best is None or key < best[0]:
            best = (key, model, prediction, params, candidate)
    _, model, prediction, params, candidate = best
    result = validation[PREDICTION_COLUMNS].copy()
    result['prediction'], result['model'] = prediction, variant
    if family == 'lightgbm':
        if not excluded:
            model.booster_.save_model(str(output / f'{variant}.txt'))
        gain = model.booster_.feature_importance(importance_type='gain')
    else:
        if not excluded:
            model.save_model(output / f'{variant}.json')
        gains = model.get_booster().get_score(importance_type='total_gain')
        gain = np.array([gains.get(c, 0) for c in xTrain.columns])
    writeJson(output / f'{variant}_metadata.json', dict(
        candidate=candidate, parameters=params, input_columns=columns, encoded_columns=xTrain.columns.tolist(),
        category_vocabulary=vocabulary, unknown_category_policy='all zero', seed=spec['seed'],
        excluded_groups=list(excluded), train_rows=len(train), validation_rows=len(validation)))
    # Aggregate one-hot levels to source feature. Native gain is descriptive, not causal.
    importance = pd.DataFrame({'feature': [c.split('__')[0] for c in xTrain.columns], 'gain': gain})
    importance = importance.groupby('feature', as_index=False).gain.sum()
    importance['gain_share'] = importance.gain / importance.gain.sum() if importance.gain.sum() else 0.0
    importance['model'] = variant
    return result, trials, importance


def demandBands(data, predictions):
    """Series groups and thresholds are fitted from eligible train labels only."""
    means = data[data.split == 'train'].groupby('series_id').demand.mean()
    lo, hi = means.quantile([1/3, 2/3])
    bands = pd.Series(np.where(means <= lo, 'low', np.where(means <= hi, 'medium', 'high')), index=means.index)
    rows = []
    for (model, band), sub in predictions.assign(band=predictions.series_id.map(bands).fillna('unseen')).groupby(['model', 'band']):
        rows.append(dict(model=model, band=band, **scoreForecast(sub.demand, sub.prediction)))
    return pd.DataFrame(rows), {'low_max_train_mean': float(lo), 'medium_max_train_mean': float(hi)}


def runExperiment(panel, orders, scenario, bounds, spec, schema, outputRoot):
    output = outputRoot / scenario
    output.mkdir(parents=True, exist_ok=True)
    features = buildScenarioFeatures(panel, bounds)
    # Exclude test completely before fitting ML, encoding, selection and artifact creation.
    features = features[features.split.isin(['train', 'validation'])].copy()
    data, fitted = buildSpatialFeatures(features, orders, bounds)
    for level, lookup in fitted.items():
        lookup.to_csv(output / f'spatial_train_{level}.csv', index=False, encoding='utf-8')
    data.to_parquet(output / 'features_train_validation.parquet', index=False)
    predictions, trials, importances = [], [], []
    for family in ['lightgbm', 'xgboost']:
        for excluded in [()] + [(g,) for g in spec['ablation_groups']]:
            result, candidateTrials, importance = fitVariant(data, family, excluded, spec, schema, output)
            predictions.append(result)
            trials.extend(candidateTrials)
            importances.append(importance)
    # Baseline uses the same temporal features and eligible validation cells.
    _, baseline = runScenario(panel[panel[DATE] <= bounds['validation'][1]], scenario, bounds)
    baseline = baseline[baseline.split == 'validation'].copy()
    expected = data.loc[data.split == 'validation', ['series_id', DATE]]
    for pred in predictions + [g for _, g in baseline.groupby('model')]:
        pd.testing.assert_frame_equal(pred[['series_id', DATE]].sort_values(['series_id', DATE]).reset_index(drop=True),
                                      expected.sort_values(['series_id', DATE]).reset_index(drop=True))
    combined = pd.concat(predictions + [baseline], ignore_index=True)
    combined['scenario'] = scenario
    metrics = evaluatePredictions(combined)
    full = metrics[metrics.model.isin(['lightgbm_full', 'xgboost_full'])]
    selected = selectOnValidation(full, scenario)
    baselineMetrics = metrics[metrics.model.isin(baseline.model.unique())]
    selectedBaseline = selectOnValidation(baselineMetrics, scenario)
    combined.to_csv(output / 'validation_predictions.csv', index=False, encoding='utf-8')
    metrics.to_csv(output / 'validation_metrics.csv', index=False, encoding='utf-8')
    pd.DataFrame(trials).to_csv(output / 'validation_search.csv', index=False, encoding='utf-8')
    pd.concat(importances).to_csv(output / 'gain_importance.csv', index=False, encoding='utf-8')
    bands, thresholds = demandBands(data, combined[combined.model.isin([selected, selectedBaseline])])
    bands.to_csv(output / 'validation_demand_bands.csv', index=False, encoding='utf-8')
    ablation = metrics[(metrics.level == 'series') & metrics.model.str.contains('_without_')].copy()
    for family in ['lightgbm', 'xgboost']:
        fullWape = metrics.loc[(metrics.level == 'series') & metrics.model.eq(family + '_full'), 'wape'].iloc[0]
        ablation.loc[ablation.model.str.startswith(family), 'delta_wape_vs_full'] = ablation.loc[
            ablation.model.str.startswith(family), 'wape'] - fullWape
    ablation.to_csv(output / 'validation_ablation.csv', index=False, encoding='utf-8')
    protocol = dict(scenario=scenario, bounds=bounds, selected_ml=selected, selected_baseline=selectedBaseline,
                    training_rows=int((data.split == 'train').sum()), validation_rows=len(expected),
                    test_scored=False, refit_on_validation=False, demand_band_thresholds=thresholds,
                    selection_note='Ablations are exploratory validation analyses; test remains unscored',
                    spec=spec, feature_schema=schema)
    writeJson(output / 'protocol.json', protocol)
    print(scenario)
    print(metrics[(metrics.level == 'series') & metrics.model.isin([selected, selectedBaseline])][['model', 'mae', 'rmse', 'wape']].to_string(index=False))
    return protocol


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', default='primary_stable_period', choices=['primary_stable_period', 'sensitivity_full_period', 'all'])
    parser.add_argument('--output-dir', type=Path, default=config.FORECASTS_DIR / 'ml_validation')
    args = parser.parse_args()
    spec = json.loads(SPEC_FILE.read_text(encoding='utf-8'))
    schema = json.loads((config.PROJECT_ROOT / 'configs/forecast_features.json').read_text(encoding='utf-8'))
    bounds = json.loads(config.STABLE_PERIOD_FILE.read_text(encoding='utf-8'))['splits']
    panel, orders = loadDemandPanel(), loadAnalysisOrders()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    writeJson(args.output_dir / 'run_manifest.json', dict(
        source_main='65dab3152f1a521fbc27114c0bf123ceb94210b9', python=platform.python_version(),
        platform=platform.platform(), versions={p: importlib.metadata.version(p) for p in ['pandas', 'numpy', 'lightgbm', 'xgboost', 'scikit-learn', 'pyarrow']},
        files_sha256={str(p.relative_to(config.PROJECT_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in [SPEC_FILE, config.PROJECT_ROOT / 'configs/forecast_features.json', config.DEMAND_PANEL_FILE, config.ANALYSIS_FILE,
                                config.PROJECT_ROOT / 'src/train_ml.py', config.PROJECT_ROOT / 'src/spatial_features.py',
                                config.PROJECT_ROOT / 'src/features.py', config.STABLE_PERIOD_FILE]},
        test_scored=False))
    for scenario, split in bounds.items():
        if args.scenario in [scenario, 'all']:
            runExperiment(panel, orders, scenario, split, spec, schema, args.output_dir)


if __name__ == '__main__':
    main()

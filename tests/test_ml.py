"""Leakage, geography, categorical encoding and persisted-model regression checks."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src import config
from src.data_loader import loadAnalysisOrders, loadDemandPanel
from src.features import buildScenarioFeatures
from src.spatial_features import SPATIAL, applySpatial, buildSpatialFeatures, fitSpatial
from src.train_ml import encodeFeatures, fitVariant, makeModel


class SpatialTests(unittest.TestCase):
    def testOriginalRegionAndFallback(self):
        orders = pd.DataFrame(dict(order_id=[1, 2, 3, 4], aoi_id=[10, 10, 11, 11],
            region_id=[1, 2, 1, 1], aoi_type=[1]*4,
            lng=[100., 120., 110., 110.], lat=[30., 40., 32., 32.]))
        fitted = fitSpatial(orders, pd.to_datetime(['2022-01-01', '2022-01-02']))
        frame = pd.DataFrame(dict(region_id=[1, 2, 1, 999], aoi_type=[1, 1, 9, 9]), index=[4, 2, 5, 1])
        got = applySpatial(frame, fitted)
        self.assertEqual(got.index.tolist(), [4, 2, 5, 1])
        np.testing.assert_allclose(got.centroid_lng[:2], [105., 120.])
        self.assertAlmostEqual(got.historical_density.iloc[0], 3/2/2)
        self.assertEqual(got.spatial_fallback.tolist(), [0, 0, 1, 2])
        # The shared AOI's original region-2 observations must not move into region 1.
        self.assertEqual(fitted['series'].n_orders.tolist(), [3, 1])

    def testAsOfAndFutureInvariance(self):
        panel = loadDemandPanel()
        orders = loadAnalysisOrders()
        bounds = json.loads(config.STABLE_PERIOD_FILE.read_text(encoding='utf-8'))['splits']['primary_stable_period']
        features = buildScenarioFeatures(panel, bounds)
        original, fitted = buildSpatialFeatures(features, orders, bounds)
        changed = orders.copy()
        after = changed.ds_date > bounds['train'][1]
        changed.loc[after, ['lng', 'lat']] = [1., 1.]
        changed.loc[after, 'region_id'] = 999
        updated, refitted = buildSpatialFeatures(features, changed, bounds)
        pd.testing.assert_frame_equal(original[SPATIAL], updated[SPATIAL])
        for level in fitted:
            pd.testing.assert_frame_equal(fitted[level], refitted[level])
        # Coordinates and counts at t cannot affect a training row at t or before t.
        cutoff = pd.Timestamp('2022-07-25')
        changed = orders.copy()
        changed.loc[changed.ds_date >= cutoff, 'lng'] = 160.
        changed = pd.concat([changed, changed[changed.ds_date >= cutoff]], ignore_index=True)
        updated, _ = buildSpatialFeatures(features, changed, bounds)
        pd.testing.assert_frame_equal(original.loc[original.ds_date <= cutoff, SPATIAL],
                                      updated.loc[updated.ds_date <= cutoff, SPATIAL])

    def testInvalidCoordinatesFailClearly(self):
        orders = pd.DataFrame(dict(order_id=[1], aoi_id=[1], region_id=[1], aoi_type=[1], lng=[0.], lat=[0.]))
        fitted = fitSpatial(orders, [pd.Timestamp('2022-01-01')])
        with self.assertRaisesRegex(ValueError, 'centroid'):
            applySpatial(orders, fitted)


class MLTests(unittest.TestCase):
    def testUnknownCategoryAndValidationVocabulary(self):
        train = pd.DataFrame(dict(region_id=[1, 2], lag_1=[1., 2.]))
        validation = pd.DataFrame(dict(region_id=[99], lag_1=[9.]))
        x, v, vocabulary = encodeFeatures(train, validation, ['region_id', 'lag_1'], ['region_id'])
        self.assertEqual(vocabulary, {'region_id': [1, 2]})
        self.assertEqual(x.columns.tolist(), v.columns.tolist())
        self.assertEqual(v.filter(like='region_id').sum(axis=1).iloc[0], 0)

    def testNativeModelRoundTripAndSeed(self):
        from lightgbm import Booster
        from xgboost import XGBRegressor
        x = pd.DataFrame({'x': np.arange(60, dtype=float)})
        y = x.x % 12
        spec = {'learning_rate': .05, 'seed': 2026, 'n_jobs': 1}
        with tempfile.TemporaryDirectory() as temp:
            for family in ['lightgbm', 'xgboost']:
                model = makeModel(family, {'n_estimators': 8}, spec).fit(x, y)
                other = makeModel(family, {'n_estimators': 8}, spec).fit(x, y)
                np.testing.assert_array_equal(model.predict(x), other.predict(x))
                path = Path(temp) / ('model.txt' if family == 'lightgbm' else 'model.json')
                if family == 'lightgbm':
                    model.booster_.save_model(str(path))
                    restored = Booster(model_file=str(path))
                else:
                    model.save_model(path)
                    restored = XGBRegressor()
                    restored.load_model(path)
                np.testing.assert_allclose(model.predict(x), restored.predict(x))

    def testSelectionIgnoresTestTargets(self):
        from src.feature_schema import featureColumns
        schema = json.loads((config.PROJECT_ROOT/'configs/forecast_features.json').read_text(encoding='utf-8'))
        spec = dict(learning_rate=.05, seed=2026, n_jobs=1,
                    lightgbm=dict(num_leaves=[3, 7], min_child_samples=[2], n_estimators=[5]))
        cols = featureColumns()
        data = pd.DataFrame({c: np.arange(30, dtype=float) % 4 for c in cols})
        data['series_id'] = 's'
        data['ds_date'] = pd.date_range('2022-01-01', periods=30)
        data['split'] = ['train']*20 + ['validation']*5 + ['test']*5
        data['demand'] = np.arange(30) % 7
        changed = data.copy()
        changed.loc[changed.split == 'test', ['demand'] + cols] = 99999
        with tempfile.TemporaryDirectory() as temp:
            a, trialsA, _ = fitVariant(data, 'lightgbm', (), spec, schema, Path(temp))
            b, trialsB, _ = fitVariant(changed, 'lightgbm', (), spec, schema, Path(temp))
        pd.testing.assert_frame_equal(a, b)
        self.assertEqual(trialsA, trialsB)


if __name__ == '__main__':
    unittest.main()

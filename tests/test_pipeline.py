"""Regression tests: order conservation, unobserved days and absence of temporal leakage."""
import unittest

import numpy as np
import pandas as pd

from src.evaluate_forecast import evaluatePredictions, selectOnValidation
from src.features import buildFeatures
from src.preprocessing import buildDemandPanel, completePanel, findMeanShifts, timeSplit
from src.train_forecast import runScenario


class PipelineTests(unittest.TestCase):
    def testConservationAndUnknownDay(self):
        df = pd.DataFrame({"region_id": [1, 2, 1], "aoi_type": [1, 1, 1], "aoi_id": [10, 10, 11],
                           "ds_date": pd.to_datetime(["2022-01-01", "2022-01-01", "2022-01-03"])})
        panel = buildDemandPanel(df)
        aoi = completePanel(df, ["aoi_id"])
        self.assertEqual(panel.demand.sum(), 3)
        self.assertEqual(aoi.demand.sum(), 3)
        self.assertFalse(panel.loc[panel.ds_date.eq("2022-01-02"), "city_observed"].any())
        self.assertEqual(aoi.loc[aoi.aoi_id.eq(10), "demand"].sum(), 2)

    def testNoCurrentOrFutureTargetLeakage(self):
        days = pd.date_range("2022-01-01", periods=50)
        panel = pd.DataFrame({"ds_date": days, "series_id": "r1_t1", "region_id": 1, "aoi_type": 1,
                              "demand": np.arange(50), "city_observed": True, "day_of_week": days.dayofweek})
        bounds = {"train": ["2022-01-01", "2022-01-25"], "validation": ["2022-01-26", "2022-02-04"],
                  "test": ["2022-02-05", "2022-02-19"]}
        f1, p1 = runScenario(panel, "test", bounds)
        changed = panel.copy()
        cutoff = pd.Timestamp("2022-02-10")
        changed.loc[changed.ds_date >= cutoff, "demand"] += 99999
        f2, p2 = runScenario(changed, "test", bounds)
        cols = ["lag_1", "lag_7", "lag_14", "rolling_mean_7", "rolling_mean_14"]
        pd.testing.assert_frame_equal(f1.loc[f1.ds_date <= cutoff, cols], f2.loc[f2.ds_date <= cutoff, cols])
        pd.testing.assert_series_equal(p1.loc[p1.ds_date <= cutoff, "prediction"],
                                       p2.loc[p2.ds_date <= cutoff, "prediction"])
        self.assertEqual(selectOnValidation(evaluatePredictions(p1), "test"),
                         selectOnValidation(evaluatePredictions(p2), "test"))
        self.assertEqual(f1.loc[f1.ds_date.eq("2022-01-15"), "rolling_mean_14"].iloc[0], 6.5)

    def testUnknownHistoryNotConvertedToZero(self):
        days = pd.date_range("2022-01-01", periods=20)
        p = pd.DataFrame({"ds_date": days, "series_id": "s", "demand": 1, "city_observed": True})
        p.loc[5, "city_observed"] = False
        f = buildFeatures(p)
        self.assertTrue(pd.isna(f.loc[6, "lag_1"]))
        self.assertFalse(f.loc[19, "history_ready"])

    def testMeanShiftAndSplit(self):
        values = np.r_[np.full(30, 5.0), np.full(30, 20.0)]
        self.assertEqual(findMeanShifts(values, maxBreaks=1, minSegment=7), [30])
        split = timeSplit(pd.date_range("2022-01-01", periods=100))
        self.assertEqual(split["train"], ["2022-01-01", "2022-03-01"])
        self.assertEqual(split["test"][1], "2022-04-10")


if __name__ == "__main__":
    unittest.main()

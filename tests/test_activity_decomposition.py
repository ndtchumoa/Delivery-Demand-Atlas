"""Regression coverage for averaging daily ratios and zero-record days."""
import unittest

import numpy as np
import pandas as pd

from src.preprocessing import decomposeActivityChange


class ActivityDecompositionTests(unittest.TestCase):
    def testWeightedProductivityWithZeroRecordDays(self):
        base = pd.DataFrame({"orders": [100, 10, 0], "activeCouriers": [10, 1, 0]})
        tail = pd.DataFrame({"orders": [9, 1], "activeCouriers": [1, 1]})
        result = decomposeActivityChange(base, tail)
        self.assertAlmostEqual(result["base"]["orders_per_courier_day"], 10)
        self.assertAlmostEqual(result["base"]["orders_per_day"], 110 / 3)
        self.assertAlmostEqual(result["order_log_ratio"],
                               result["courier_log_ratio"] + result["productivity_log_ratio"])
        # Vary both activity and daily productivity: mean of ratios breaks the identity.
        base.loc[1, "orders"] = 1
        result = decomposeActivityChange(base, tail)
        self.assertAlmostEqual(result["base"]["orders_per_courier_day"], 101 / 11)
        self.assertAlmostEqual(result["order_log_ratio"],
                               result["courier_log_ratio"] + result["productivity_log_ratio"])
        wrong = np.log((101 / 3) / 5) - np.log((11 / 3) / 1) - np.log(5.5 / 5)
        self.assertGreater(abs(wrong), 0.1)

    def testUnchangedMeanHasNoShare(self):
        frame = pd.DataFrame({"orders": [10, 20], "activeCouriers": [1, 2]})
        self.assertIsNone(decomposeActivityChange(frame, frame)["courier_log_share"])

    def testZeroTotalsAreNotFiniteLogRatios(self):
        zero = pd.DataFrame({"orders": [0], "activeCouriers": [0]})
        with self.assertRaises(ValueError):
            decomposeActivityChange(zero, zero)

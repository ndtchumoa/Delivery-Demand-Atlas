import unittest

import pandas as pd

from src.config import DEMAND_DATE_COLUMN as DATE
from src.regional_time_series import buildRegionalPanel, compareRegions, summarizeRegions


class RegionalTimeSeriesTests(unittest.TestCase):
    def setUp(self):
        self.raw = pd.DataFrame({
            "order_id": list(range(5)),
            "region_id": [31, 53, 31, 31, 53],
            "ds": ["0512", "0512", "0513", "0515", "0515"],
            "accept_time": ["05-12 10:00:00", "05-12 10:00:00", "05-13 10:00:00",
                            "05-15 10:00:00", "05-15 10:00:00"],
            "delivery_time": ["05-14 12:00:00", "05-12 12:00:00", "05-13 12:00:00",
                              "05-15 12:00:00", "05-15 12:00:00"],
            "accept_gps_lng": [0.0] * 5,
            "accept_gps_lat": [0.0] * 5,
            "delivery_gps_lng": [0.0] * 5,
            "delivery_gps_lat": [0.0] * 5,
        })

    def test_preserves_orders_and_distinguishes_missing_from_zero(self):
        panel = buildRegionalPanel(self.raw)
        demand = panel.pivot(index=DATE, columns="region_id", values="demand")
        self.assertEqual(int(panel["demand"].sum()), len(self.raw))
        self.assertEqual(demand[53].iloc[1], 0)
        self.assertTrue(demand.iloc[2].isna().all())
        self.assertEqual(summarizeRegions(panel)["zero_days"].tolist(), [0, 1])

    def test_changes_do_not_bridge_calendar_gaps(self):
        panel = buildRegionalPanel(self.raw)
        for data in (panel, panel.loc[panel["city_observed"]]):
            stats = compareRegions(data).set_index("transform")
            self.assertEqual(stats.loc["level", "paired_days"], 3)
            self.assertEqual(stats.loc["daily_change", "paired_days"], 1)
            self.assertTrue(pd.isna(stats.loc["daily_change", "pearson_r"]))

    def test_rejects_duplicate_ids_and_conflicting_dates(self):
        with self.assertRaisesRegex(ValueError, "order_id"):
            buildRegionalPanel(pd.concat([self.raw, self.raw.iloc[:1]]))
        self.raw.loc[0, "ds"] = "0513"
        with self.assertRaisesRegex(ValueError, "acceptance date"):
            buildRegionalPanel(self.raw)

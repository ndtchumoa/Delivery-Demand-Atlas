import unittest

import h3
import pandas as pd

from src.spatial_aggregation import auditCoordinates, compareResolutions, countOrdersByCell


class SpatialAggregationTests(unittest.TestCase):
    def test_classifies_invalid_coordinates_and_preserves_valid_orders(self):
        orders = pd.DataFrame({
            "order_id": [1, 2, 3, 4, 5, 6, 7],
            "region_id": [31, 31, 31, 53, 53, 53, 53],
            "lng": ["126.55", None, 0, 181, "bad", 126.65, float("inf")],
            "lat": [43.8, 43.8, 0, 43.9, 43.9, 44.1, 43.9],
        })
        mappable, coverage = auditCoordinates(orders)
        self.assertEqual(mappable["order_id"].tolist(), [1, 6])
        self.assertEqual(mappable["lng"].tolist(), [126.55, 126.65])
        city = coverage.loc[coverage["scope"].eq("city")].iloc[0]
        self.assertEqual(city["missing_or_non_numeric"], 2)
        self.assertEqual(city["out_of_range"], 2)
        self.assertEqual(city["zero_pair"], 1)
        self.assertEqual(city["excluded_orders"], 5)
        self.assertAlmostEqual(city["coverage_pct"], 200 / 7)

    def test_maps_known_point_and_conserves_counts_at_both_resolutions(self):
        orders = pd.DataFrame({"lat": [37.769377] * 6, "lng": [-122.388903] * 6})
        counts = {level: countOrdersByCell(orders, level) for level in (8, 9)}
        self.assertEqual(counts[9].to_dict(), {"89283082e73ffff": 6})
        for level, values in counts.items():
            self.assertEqual(h3.get_resolution(values.index[0]), level)
        result = compareResolutions(counts)
        self.assertEqual(result["mapped_orders"].tolist(), [6, 6])
        self.assertEqual(result["sparse_cells"].tolist(), [0, 0])

    def test_sparse_metrics_include_five_orders_and_handle_empty_data(self):
        result = compareResolutions({8: pd.Series([1, 5, 6]), 9: pd.Series(dtype=int)})
        level_eight, level_nine = result.iloc[0], result.iloc[1]
        self.assertEqual(level_eight["sparse_cells"], 2)
        self.assertEqual(level_eight["orders_in_sparse_cells"], 6)
        self.assertAlmostEqual(level_eight["sparse_cells_pct"], 200 / 3)
        self.assertEqual(level_eight["orders_in_sparse_cells_pct"], 50)
        self.assertTrue(pd.isna(level_nine["sparse_cells_pct"]))

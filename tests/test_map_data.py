import json
import unittest

import h3
import pandas as pd

from src.map_data import MAP_RESOLUTION, buildMapData


class MapDataTests(unittest.TestCase):
    def setUp(self):
        self.raw = pd.DataFrame({
            "order_id": [1, 2, 3, 4, 5],
            "ds": ["0512", "0512", "0512", "0514", "0515"],
            "accept_time": ["05-12 10:00:00"] * 3 + ["05-14 10:00:00", "05-15 10:00:00"],
            "delivery_time": ["05-12 11:00:00"] * 3 + ["05-14 11:00:00", "05-15 11:00:00"],
            "region_id": [31, 31, 53, 53, 31],
            "aoi_type": [1, 1, 2, 1, 1],
            "lng": [126.56, 126.56, 126.56, 0.0, 126.60],
            "lat": [43.84, 43.84, 43.84, 0.0, 43.90],
            "accept_gps_lng": [0.0] * 5,
            "accept_gps_lat": [0.0] * 5,
            "delivery_gps_lng": [0.0] * 5,
            "delivery_gps_lat": [0.0] * 5,
        })

    def test_preserves_filter_dimensions_and_missing_days(self):
        geometry, demand = buildMapData(self.raw)
        first = h3.latlng_to_cell(43.84, 126.56, MAP_RESOLUTION)
        second = h3.latlng_to_cell(43.90, 126.60, MAP_RESOLUTION)
        self.assertEqual(demand["total_orders"], 5)
        self.assertEqual(demand["mapped_orders"], 4)
        self.assertEqual(demand["row_fields"], ["h3_cell", "region_id", "aoi_type", "orders"])
        self.assertEqual(demand["orders_by_date"], {
            "2022-05-12": [[first, 31, 1, 2], [first, 53, 2, 1]],
            "2022-05-15": [[second, 31, 1, 1]],
        })
        self.assertFalse(demand["calendar"]["2022-05-13"])
        self.assertTrue(demand["calendar"]["2022-05-14"])
        self.assertEqual({feature["id"] for feature in geometry["features"]}, {first, second})
        json.dumps(demand, allow_nan=False)

    def test_geometry_uses_h3_8_and_closed_longitude_latitude_rings(self):
        geometry, _ = buildMapData(self.raw)
        self.assertEqual(geometry["type"], "FeatureCollection")
        for feature in geometry["features"]:
            self.assertEqual(h3.get_resolution(feature["id"]), 8)
            self.assertEqual(feature["geometry"]["type"], "Polygon")
            ring = feature["geometry"]["coordinates"][0]
            self.assertEqual(ring[0], ring[-1])
            self.assertTrue(all(126 < lon < 127 and 43 < lat < 44 for lon, lat in ring))
            area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:]))
            self.assertGreater(area, 0)

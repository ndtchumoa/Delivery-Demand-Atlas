"""Export H3 geometry and observed delivery demand for the Jilin atlas."""
import argparse
import json
from pathlib import Path

import h3
import pandas as pd

from . import config
from .data_loader import loadRawDelivery
from .preprocessing import validateDemandOrders
from .spatial_aggregation import assignH3Cells, auditCoordinates

DATE = config.DEMAND_DATE_COLUMN
MAP_RESOLUTION = 8
OUTPUT_DIR = config.PROJECT_ROOT / "demo" / "data"


def cellFeature(cell: str) -> dict:
    """Make a GeoJSON polygon with a closed counterclockwise exterior ring."""
    ring = [[round(lng, 6), round(lat, 6)] for lat, lng in h3.cell_to_boundary(cell)]
    ring.append(ring[0])
    signed_area = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:]))
    if signed_area < 0:
        ring.reverse()
    return {
        "type": "Feature",
        "id": cell,
        "properties": {},
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }


def buildMapData(raw: pd.DataFrame) -> tuple[dict, dict]:
    """Return map geometry and sparse counts for the validated input orders."""
    orders = validateDemandOrders(raw)
    if orders["aoi_type"].isna().any():
        raise ValueError("Missing aoi_type; resolve before exporting map data.")

    mappable, _ = auditCoordinates(orders)
    mappable["h3_cell"] = assignH3Cells(mappable, MAP_RESOLUTION)
    dimensions = ["h3_cell", "region_id", "aoi_type"]
    counts = mappable.groupby([DATE, *dimensions]).size().rename("orders").reset_index()
    if int(counts["orders"].sum()) != len(mappable):
        raise RuntimeError("Map aggregation did not preserve the number of mappable orders.")

    calendar = pd.date_range(orders[DATE].min(), orders[DATE].max())
    observed = set(orders[DATE])
    demand = {
        "h3_resolution": MAP_RESOLUTION,
        "row_fields": [*dimensions, "orders"],
        "calendar": {day.strftime("%Y-%m-%d"): day in observed for day in calendar},
        "total_orders": len(orders),
        "mapped_orders": len(mappable),
        "orders_by_date": {
            day.strftime("%Y-%m-%d"): [list(row) for row in group[[*dimensions, "orders"]]
                                       .itertuples(index=False, name=None)]
            for day, group in counts.groupby(DATE)
        },
    }
    features = [cellFeature(cell) for cell in sorted(counts["h3_cell"].unique())]
    return {"type": "FeatureCollection", "features": features}, demand


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Path to the raw Jilin CSV.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    geometry, demand = buildMapData(loadRawDelivery(args.input))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in (("h3_cells.geojson", geometry), ("daily_cell_demand.json", demand)):
        target = args.output_dir / name
        target.write_text(json.dumps(content, separators=(",", ":")) + "\n",
                          encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()

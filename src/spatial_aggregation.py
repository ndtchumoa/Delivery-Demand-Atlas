"""Audit delivery coordinates and compare H3 resolutions for Jilin."""
import argparse
from pathlib import Path

import h3
import pandas as pd

from . import config
from .data_loader import loadRawDelivery
from .preprocessing import validateDemandOrders

RESOLUTIONS = (8, 9)
SPARSE_CELL_MAX_ORDERS = 5
OUTPUT_DIR = config.PROJECT_ROOT / "outputs" / "analysis"


def auditCoordinates(orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return mappable orders and coverage at city and regional levels."""
    if orders["region_id"].isna().any():
        raise ValueError("Missing region_id; resolve before summarizing coverage.")

    coords = orders[["lng", "lat"]].apply(pd.to_numeric, errors="coerce")
    status = pd.Series("valid", index=orders.index, dtype="str")
    in_range = coords["lng"].between(-180, 180) & coords["lat"].between(-90, 90)
    status.loc[~in_range] = "out_of_range"
    status.loc[coords.isna().any(axis=1)] = "missing_or_non_numeric"
    status.loc[coords["lng"].eq(0) & coords["lat"].eq(0)] = "zero_pair"

    def summarize(scope: str, region_id: str, values: pd.Series) -> dict:
        counts = values.value_counts()
        valid = int(counts.get("valid", 0))
        return {
            "scope": scope,
            "region_id": region_id,
            "total_orders": len(values),
            "mappable_orders": valid,
            "excluded_orders": len(values) - valid,
            "missing_or_non_numeric": int(counts.get("missing_or_non_numeric", 0)),
            "out_of_range": int(counts.get("out_of_range", 0)),
            "zero_pair": int(counts.get("zero_pair", 0)),
            "coverage_pct": 100 * valid / len(values) if len(values) else None,
        }

    records = [summarize("city", "", status)]
    records.extend(summarize("region", str(region), values)
                   for region, values in status.groupby(orders["region_id"], sort=True))
    valid = status.eq("valid")
    mappable = orders.loc[valid].copy()
    mappable[["lng", "lat"]] = coords.loc[valid]
    return mappable, pd.DataFrame.from_records(records)


def assignH3Cells(orders: pd.DataFrame, resolution: int) -> pd.Series:
    """Assign each mappable order to exactly one cell at the requested resolution."""
    cells = [h3.latlng_to_cell(lat, lng, resolution)
             for lat, lng in zip(orders["lat"], orders["lng"])]
    return pd.Series(cells, index=orders.index, name="h3_cell", dtype="str")


def countOrdersByCell(orders: pd.DataFrame, resolution: int) -> pd.Series:
    return assignH3Cells(orders, resolution).value_counts().sort_index()


def compareResolutions(cell_counts: dict[int, pd.Series]) -> pd.DataFrame:
    """Compare occupied cells and the number of orders in sparse cells over the full period."""
    records = []
    for resolution, counts in cell_counts.items():
        sparse = counts.le(SPARSE_CELL_MAX_ORDERS)
        cells = len(counts)
        orders = int(counts.sum())
        sparse_cells = int(sparse.sum())
        sparse_orders = int(counts.loc[sparse].sum())
        records.append({
            "resolution": resolution,
            "mapped_orders": orders,
            "occupied_cells": cells,
            "median_orders_per_cell": counts.median() if cells else None,
            "sparse_cell_max_orders": SPARSE_CELL_MAX_ORDERS,
            "sparse_cells": sparse_cells,
            "sparse_cells_pct": 100 * sparse_cells / cells if cells else None,
            "orders_in_sparse_cells": sparse_orders,
            "orders_in_sparse_cells_pct": 100 * sparse_orders / orders if orders else None,
        })
    return pd.DataFrame.from_records(records)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Path to the raw Jilin CSV.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    orders = validateDemandOrders(loadRawDelivery(args.input))
    mappable, coverage = auditCoordinates(orders)
    cell_counts = {level: countOrdersByCell(mappable, level) for level in RESOLUTIONS}
    comparison = compareResolutions(cell_counts)
    if not comparison["mapped_orders"].eq(len(mappable)).all():
        raise RuntimeError("Mapped order totals do not match the coordinate audit.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    options = {"index": False, "lineterminator": "\n", "float_format": "%.6f"}
    coverage.to_csv(args.output_dir / "spatial_coverage.csv", **options)
    comparison.to_csv(args.output_dir / "h3_resolution_comparison.csv", **options)


if __name__ == "__main__":
    main()

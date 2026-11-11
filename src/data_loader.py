"""Data loading for raw and processed tables.

Logic: the raw LaDe-D Jilin CSV is read once; `ds` is kept as a string so that the leading zero
of dates such as "0512" is preserved. The literal text "nan" in the GPS columns is parsed to NaN.
Processed tables are read back with the dtypes the pipeline expects.

Complexity: O(n) time and memory in the number of rows n (single pass parse).
"""
from pathlib import Path
from typing import Optional

import pandas as pd

from . import config


def loadRawDelivery(path: Optional[Path] = None) -> pd.DataFrame:
    """Load delivery_jl.csv without any cleaning or row removal."""
    filePath = Path(path) if path is not None else config.RAW_DIR / config.RAW_FILE_NAME
    return pd.read_csv(filePath, dtype={"ds": str})


def loadAnalysisOrders() -> pd.DataFrame:
    """Orders after the cleaning rules (flags retained)."""
    return pd.read_parquet(config.ANALYSIS_FILE)


def loadDemandPanel() -> pd.DataFrame:
    """Forecast table, one row per region_id x aoi_type x day."""
    return pd.read_csv(config.DEMAND_PANEL_FILE, parse_dates=[config.DEMAND_DATE_COLUMN])

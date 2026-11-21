"""Load raw LaDe-D Jilin orders."""
from pathlib import Path

import pandas as pd

from . import config


def loadRawDelivery(path: Path | None = None) -> pd.DataFrame:
    """Preserve leading zeros in the source month-day field."""
    source = Path(path) if path is not None else config.RAW_DIR / config.RAW_FILE_NAME
    return pd.read_csv(source, dtype={"ds": str})

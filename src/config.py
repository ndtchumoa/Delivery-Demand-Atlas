"""Paths and date conventions for the LaDe-D Jilin dataset."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_FILE_NAME = "delivery_jl.csv"

# The source gives month and day without a year.
ASSUMED_YEAR = 2022
DEMAND_DATE_COLUMN = "ds_date"

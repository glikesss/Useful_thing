"""Public API for experimental data management and processing."""

from .csv_loader import (
    load_csv_file,
    load_csv_files,
    merge_csv_files,
)
from .data_manager import DataManager
from .experiment import Experiment
from .processing import (
    derivative,
    drop_missing,
    filter_rows,
    integrate,
    select_columns,
    smooth,
    statistics,
)

__all__ = [
    "DataManager",
    "Experiment",
    "load_csv_file",
    "load_csv_files",
    "merge_csv_files",
    "select_columns",
    "drop_missing",
    "filter_rows",
    "smooth",
    "derivative",
    "integrate",
    "statistics",
]

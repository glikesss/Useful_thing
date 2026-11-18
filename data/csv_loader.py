from os import PathLike
from pathlib import Path

import pandas as pd


def load_csv_file(path, **kwargs):
    """Load one CSV file into a DataFrame."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(path)

    if not path.is_file():
        raise IsADirectoryError(path)

    try:
        return pd.read_csv(path, **kwargs)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"CSV file is empty: {path}") from exc


def load_csv_files(
    paths,
    *,
    ignore_index=True,
    sort_columns=False,
    **kwargs,
):
    """
    Load and vertically concatenate CSV files.

    Columns are aligned by name. Missing values are filled with NaN.
    CSV files are processed in the order supplied.
    """
    if isinstance(paths, (str, PathLike)):
        paths = [paths]
    else:
        try:
            paths = list(paths)
        except TypeError as exc:
            raise TypeError("paths must be a path or an iterable of paths") from exc

    if not paths:
        raise ValueError("At least one CSV file must be provided")

    frames = [load_csv_file(path, **kwargs) for path in paths]

    return pd.concat(
        frames,
        ignore_index=ignore_index,
        sort=sort_columns,
    )


def merge_csv_files(paths, output_path, *, index=False, **kwargs):
    """Merge CSV files, save the result and return the DataFrame."""
    result = load_csv_files(paths, **kwargs)
    result.to_csv(output_path, index=index)
    return result

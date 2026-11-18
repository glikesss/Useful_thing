import csv
from os import PathLike
from pathlib import Path

import pandas as pd


def load_csv_file(path, **kwargs):
    """Load one CSV file with automatic delimiter detection."""
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(path)

    if not path.is_file():
        raise IsADirectoryError(path)

    try:
        with path.open(
            "r",
            encoding=kwargs.get("encoding", "utf-8-sig"),
            newline="",
        ) as file:
            sample = file.read(65536)

        if "sep" not in kwargs and "delimiter" not in kwargs:
            try:
                dialect = csv.Sniffer().sniff(
                    sample,
                    delimiters=",;\t|",
                )
                kwargs["sep"] = dialect.delimiter
            except csv.Error:
                kwargs["sep"] = ","

        separator = kwargs.get("sep", kwargs.get("delimiter", ","))
        if (
            "decimal" not in kwargs
            and separator != ","
            and __import__("re").search(
                r"(?<![\w])[-+]?\d+,\d+(?:[eE][-+]?\d+)?",
                sample,
            )
        ):
            kwargs["decimal"] = ","

        frame = pd.read_csv(path, **kwargs)
        for column in frame.select_dtypes(include=["object", "string"]).columns:
            frame[column] = frame[column].str.strip()

        if kwargs.get("header", "infer") == "infer" and "names" not in kwargs and not frame.empty:
            units = frame.iloc[0].astype("string").str.strip()
            if units.notna().all() and units.str.fullmatch(r"\([^()]+\)").all():
                frame.columns = [
                    f"{column} {unit}"
                    for column, unit in zip(frame.columns, units)
                ]
                frame = frame.iloc[1:].reset_index(drop=True)

        for column in frame.columns:
            values = frame[column].astype("string").str.strip()
            normalized = (
                values.str.replace(",", ".", regex=False)
                if kwargs.get("decimal") == ","
                else values
            )
            converted = pd.to_numeric(normalized, errors="coerce")
            non_empty = values.notna() & values.ne("")

            if non_empty.any() and converted[non_empty].notna().all():
                frame[column] = converted

        return frame

    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"CSV file is empty: {path}") from exc


def load_csv_files(
    paths,
    *,
    ignore_index=True,
    sort_columns=False,
    **kwargs,
):
    """Load and vertically concatenate CSV files."""
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


def save_csv_file(
    data,
    output_path,
    *,
    sep=",",
    decimal=".",
    index=False,
    encoding="utf-8-sig",
):
    """Save a DataFrame to CSV with configurable formatting."""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")

    if len(sep) != 1 or len(decimal) != 1:
        raise ValueError("sep and decimal must be single characters")

    if sep == decimal:
        raise ValueError("sep and decimal must be different")

    output_path = Path(output_path)
    data.to_csv(
        output_path,
        sep=sep,
        decimal=decimal,
        index=index,
        encoding=encoding,
    )
    return output_path
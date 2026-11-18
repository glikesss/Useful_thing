import numpy as np
import pandas as pd
from scipy.integrate import trapezoid


def _validate_dataframe(data):
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")


def _validate_column(data, column):
    if column not in data.columns:
        raise KeyError(f"Unknown column: {column}")


def select_columns(data, columns):
    _validate_dataframe(data)
    columns = list(columns)

    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise KeyError(f"Unknown columns: {missing}")

    return data.loc[:, columns].copy()


def drop_missing(data, *, subset=None, how="any"):
    _validate_dataframe(data)
    return data.dropna(subset=subset, how=how).copy()


def filter_rows(data, column, *, minimum=None, maximum=None):
    _validate_dataframe(data)
    _validate_column(data, column)

    if minimum is None and maximum is None:
        raise ValueError("At least one bound must be specified")

    mask = pd.Series(True, index=data.index)

    if minimum is not None:
        mask &= data[column] >= minimum

    if maximum is not None:
        mask &= data[column] <= maximum

    return data.loc[mask].copy()


def smooth(data, column, *, window=3, result_column=None):
    _validate_dataframe(data)
    _validate_column(data, column)

    if not isinstance(window, int) or isinstance(window, bool) or window < 1:
        raise ValueError("window must be a positive integer")

    values = pd.to_numeric(data[column], errors="raise")
    if np.isinf(values.to_numpy(dtype=float, na_value=np.nan)).any():
        raise ValueError("Input column must not contain infinite values")

    result = data.copy()
    output_column = result_column or f"{column}_smoothed"

    result[output_column] = (
        pd.to_numeric(result[column], errors="raise")
        .rolling(window=window, center=True, min_periods=1)
        .mean()
    )

    return result


def derivative(
    data,
    value_column,
    *,
    x_column=None,
    result_column=None,
):
    _validate_dataframe(data)
    _validate_column(data, value_column)

    y = pd.to_numeric(data[value_column], errors="raise").to_numpy(dtype=float)

    if len(y) < 2:
        raise ValueError("At least two data points are required")

    if x_column is None:
        x = np.arange(len(data), dtype=float)
    else:
        _validate_column(data, x_column)
        x = pd.to_numeric(data[x_column], errors="raise").to_numpy(dtype=float)

    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("Input columns must contain finite numeric values")

    dx = np.diff(x)
    if np.any(dx <= 0):
        raise ValueError("x values must be strictly increasing")

    # Forward finite differences: each interval's slope belongs to its
    # left-hand row. The final row reuses the last available interval slope.
    slopes = np.diff(y) / dx
    derivative_values = np.empty_like(y)
    derivative_values[:-1] = slopes
    derivative_values[-1] = slopes[-1]

    result = data.copy()
    output_column = result_column or f"d_{value_column}_d_{x_column or 'index'}"
    result[output_column] = derivative_values

    return result


def integrate(data, value_column, *, x_column=None):
    _validate_dataframe(data)
    _validate_column(data, value_column)

    y = pd.to_numeric(data[value_column], errors="raise").to_numpy(dtype=float)

    if len(y) < 2:
        raise ValueError("At least two data points are required")

    if x_column is None:
        x = np.arange(len(data), dtype=float)
    else:
        _validate_column(data, x_column)
        x = pd.to_numeric(data[x_column], errors="raise").to_numpy(dtype=float)

    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise ValueError("Input columns must contain finite numeric values")

    if np.any(np.diff(x) <= 0):
        raise ValueError("x values must be strictly increasing")

    return float(trapezoid(y, x))


def statistics(data, *, columns=None):
    _validate_dataframe(data)

    selected = data if columns is None else select_columns(data, columns)
    numeric = selected.select_dtypes(include="number")

    if numeric.empty:
        raise ValueError("No numeric columns available")

    return numeric.describe()

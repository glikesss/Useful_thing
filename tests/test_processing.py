import numpy as np
import pandas as pd
import pytest

from data.processing import (
    derivative,
    drop_missing,
    filter_rows,
    integrate,
    select_columns,
    smooth,
    statistics,
)


def test_select_columns():
    data = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    result = select_columns(data, ["y"])

    assert list(result.columns) == ["y"]
    assert result["y"].tolist() == [3, 4]


def test_select_columns_rejects_missing_column():
    with pytest.raises(KeyError):
        select_columns(pd.DataFrame({"x": [1]}), ["missing"])


def test_drop_missing():
    data = pd.DataFrame({"x": [1, None, 3], "y": [4, 5, 6]})
    result = drop_missing(data)

    assert len(result) == 2
    assert result["x"].tolist() == [1, 3]


def test_drop_missing_subset():
    data = pd.DataFrame({"x": [1, None], "y": [None, 2]})
    result = drop_missing(data, subset=["x"])

    assert len(result) == 1
    assert pd.isna(result.iloc[0]["y"])


def test_filter_rows():
    data = pd.DataFrame({"x": [1, 2, 3, 4]})
    result = filter_rows(data, "x", minimum=2, maximum=3)

    assert result["x"].tolist() == [2, 3]


def test_filter_rows_requires_bound():
    with pytest.raises(ValueError):
        filter_rows(pd.DataFrame({"x": [1]}), "x")


def test_smooth():
    data = pd.DataFrame({"x": [0, 3, 0, 3, 0]})
    result = smooth(data, "x", window=3)

    assert "x_smoothed" in result
    assert result["x_smoothed"].iloc[2] == 2


def test_smooth_rejects_invalid_window():
    with pytest.raises(ValueError):
        smooth(pd.DataFrame({"x": [1, 2]}), "x", window=0)


def test_derivative():
    data = pd.DataFrame({"time": [0, 1, 2, 3], "position": [0, 2, 4, 6]})
    result = derivative(data, "position", x_column="time")

    np.testing.assert_allclose(result["d_position_d_time"], [2, 2, 2, 2])


def test_derivative_uses_adjacent_rows_and_preserves_scale():
    data = pd.DataFrame({
        "time": [0.0, 1.0, 2.0, 3.0],
        "signal": [0.0, 2.0, 6.0, 12.0],
    })

    result = derivative(data, "signal", x_column="time")

    np.testing.assert_allclose(
        result["d_signal_d_time"],
        [2.0, 4.0, 6.0, 6.0],
    )


def test_derivative_uses_actual_nonuniform_x_spacing():
    data = pd.DataFrame({
        "time": [0.0, 2.0, 5.0],
        "signal": [0.0, 8.0, 23.0],
    })

    result = derivative(data, "signal", x_column="time")

    np.testing.assert_allclose(result["d_signal_d_time"], [4.0, 5.0, 5.0])


def test_derivative_rejects_non_increasing_x():
    data = pd.DataFrame({"time": [0.0, 2.0, 1.0], "signal": [0.0, 4.0, 3.0]})

    with pytest.raises(ValueError, match="strictly increasing"):
        derivative(data, "signal", x_column="time")


def test_derivative_rejects_single_point():
    with pytest.raises(ValueError):
        derivative(pd.DataFrame({"x": [1]}), "x")


def test_integrate():
    data = pd.DataFrame({"time": [0, 1, 2], "value": [0, 2, 4]})

    result = integrate(data, "value", x_column="time")

    assert result == pytest.approx(4.0)


def test_integrate_rejects_non_increasing_x():
    data = pd.DataFrame({"time": [0, 1, 1], "value": [0, 2, 4]})

    with pytest.raises(ValueError):
        integrate(data, "value", x_column="time")


def test_statistics():
    data = pd.DataFrame({"x": [1, 2, 3], "name": ["a", "b", "c"]})
    result = statistics(data)

    assert "x" in result.columns
    assert result.loc["mean", "x"] == 2


def test_statistics_selected_columns():
    data = pd.DataFrame({"x": [1, 2], "y": [10, 20]})
    result = statistics(data, columns=["y"])

    assert list(result.columns) == ["y"]


def test_processing_rejects_non_dataframe():
    with pytest.raises(TypeError):
        drop_missing([1, 2, 3])

import pandas as pd
import pytest
from data.processing import smooth

def test_smooth_allows_nan():
    df = pd.DataFrame({"y": [1.0, float("nan"), 3.0]})
    result = smooth(df, "y")
    assert result["y_smoothed"].tolist() == [1.0, 2.0, 3.0]

@pytest.mark.parametrize("value", [float("inf"), float("-inf")])
def test_smooth_rejects_infinity(value):
    df = pd.DataFrame({"y": [1.0, value, 3.0]})
    with pytest.raises(ValueError, match="finite"):
        smooth(df, "y")

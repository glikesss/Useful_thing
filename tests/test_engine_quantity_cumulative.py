
import numpy as np
import pytest

from core import MathEngine
from core.errors import DimensionError
from units.quantities import Quantity
from units.dimensions import LENGTH, TIME


def test_quantity_cumulative_integral():
    engine = MathEngine()

    result = engine.cumulative(
        "3 * m / s",
        values=[1, 2, 3],
        variable="t",
        start=Quantity(0, TIME),
    )

    assert isinstance(result, Quantity)
    assert result.dimension == LENGTH
    assert np.allclose(result.value, [3, 6, 9])


def test_quantity_cumulative_with_global_variable():
    engine = MathEngine()
    engine.set_lines(["velocity = 3 * m / s"])

    result = engine.cumulative(
        "velocity",
        values=[1, 2, 3],
        variable="t",
        start=Quantity(0, TIME),
    )

    assert isinstance(result, Quantity)
    assert result.dimension == LENGTH
    assert np.allclose(result.value, [3, 6, 9])


def test_quantity_cumulative_empty_array():
    engine = MathEngine()

    result = engine.cumulative(
        "3 * m / s",
        values=[],
        variable="t",
        start=Quantity(0, TIME),
    )

    assert isinstance(result, Quantity)
    assert result.dimension == LENGTH
    assert len(result.value) == 0


def test_quantity_cumulative_dimension_mismatch():
    engine = MathEngine()

    with pytest.raises(DimensionError):
        engine.cumulative(
            "3 * m / s",
            values=[
                Quantity(1, TIME),
                Quantity(2, LENGTH),
            ],
            variable="t",
            start=Quantity(0, TIME),
        )


def test_quantity_cumulative_non_monotonic_values():
    engine = MathEngine()

    with pytest.raises(Exception):
        engine.cumulative(
            "3 * m / s",
            values=[
                Quantity(1, TIME),
                Quantity(3, TIME),
                Quantity(2, TIME),
            ],
            variable="t",
            start=Quantity(0, TIME),
        )


def test_symbolic_quantity_cumulative_integral():
    engine = MathEngine()
    engine.set_symbolic_variable("t", "t", TIME)

    result = engine.cumulative(
        "3*t",
        values=[1, 2, 3],
        variable="t",
        start=0,
    )

    assert isinstance(result, Quantity)
    assert result.dimension == TIME ** 2
    assert np.allclose(result.value, [1.5, 6.0, 13.5])


def test_symbolic_quantity_cumulative_empty_array():
    engine = MathEngine()
    engine.set_symbolic_variable("t", "t", TIME)

    result = engine.cumulative(
        "3*t",
        values=[],
        variable="t",
        start=0,
    )

    assert isinstance(result, Quantity)
    assert result.dimension == TIME ** 2
    assert len(result.value) == 0

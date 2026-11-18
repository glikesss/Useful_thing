
import pytest

from core import MathEngine
from core.errors import DimensionError
from units.quantities import Quantity
from units.dimensions import LENGTH, TIME


def test_quantity_definite_integral():
    engine = MathEngine()

    result = engine.integrate(
        "3 * m / s",
        variable="t",
        lower=Quantity(0, TIME),
        upper=Quantity(2, TIME),
    )

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(6)
    assert result.dimension == LENGTH


def test_quantity_integral_with_global_variable():
    engine = MathEngine()
    engine.set_lines(["velocity = 3 * m / s"])

    result = engine.integrate(
        "velocity",
        variable="t",
        lower=Quantity(0, TIME),
        upper=Quantity(2, TIME),
    )

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(6)
    assert result.dimension == LENGTH


def test_quantity_integral_reverse_bounds():
    engine = MathEngine()

    result = engine.integrate(
        "3 * m / s",
        variable="t",
        lower=Quantity(2, TIME),
        upper=Quantity(0, TIME),
    )

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(-6)
    assert result.dimension == LENGTH


def test_quantity_integral_dimension_mismatch():
    engine = MathEngine()

    with pytest.raises(DimensionError):
        engine.integrate(
            "3 * m / s",
            variable="t",
            lower=Quantity(0, TIME),
            upper=Quantity(2, LENGTH),
        )

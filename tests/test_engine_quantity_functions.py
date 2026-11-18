
import pytest

from core import MathEngine
from units.quantities import Quantity
from units.dimensions import LENGTH, TIME, FORCE


def make_engine():
    engine = MathEngine()
    engine.set_lines([
        "mass = 2 * kg",
        "acceleration = 9.81 * m / s**2",
        "F(m, a) = m * a",
        "double(x) = 2 * x",
        "scale(x, factor=3) = x * factor",
        "G(x) = double(x) + x",
        "ordinary(x) = x**2 + 1",
    ])
    return engine


def test_quantity_function_call():
    engine = make_engine()

    result = engine.call(
        "F",
        engine.get_variable("mass"),
        engine.get_variable("acceleration"),
    )

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(19.62)
    assert result.dimension == FORCE


def test_quantity_function_in_expression():
    engine = make_engine()

    result = engine.evaluate("F(mass, acceleration)")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(19.62)
    assert result.dimension == FORCE


def test_nested_quantity_functions():
    engine = make_engine()

    result = engine.evaluate("G(5 * m)")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(15)
    assert result.dimension == LENGTH


def test_quantity_function_default_argument():
    engine = make_engine()

    result = engine.call(
        "scale",
        Quantity(4, LENGTH),
    )

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(12)
    assert result.dimension == LENGTH


def test_quantity_function_keyword_argument():
    engine = make_engine()

    result = engine.call(
        "scale",
        Quantity(4, LENGTH),
        factor=5,
    )

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(20)
    assert result.dimension == LENGTH


def test_ordinary_function_still_works():
    engine = make_engine()

    assert engine.call("ordinary", 3) == pytest.approx(10)


def test_ordinary_function_in_expression():
    engine = make_engine()

    assert engine.evaluate("ordinary(3)") == pytest.approx(10)

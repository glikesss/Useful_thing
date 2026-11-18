
import pytest
import sympy as sp

from core import MathEngine
from units.quantities import Quantity
from units.dimensions import LENGTH, MASS


def test_ordinary_symbolic_derivative():
    engine = MathEngine()

    result = engine.differentiate("x**3", "x")

    assert sp.simplify(result - 3 * sp.Symbol("x")**2) == 0


def test_quantity_derivative():
    engine = MathEngine()
    engine.set_lines([
        "x = 5 * m",
    ])

    result = engine.differentiate("x**2", "x")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(10)
    assert result.dimension == LENGTH


def test_quantity_derivative_with_global_coefficient():
    engine = MathEngine()
    engine.set_lines([
        "mass = 2 * kg",
        "x = 5 * m",
    ])

    result = engine.differentiate("mass * x**2", "x")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(20)
    assert result.dimension == MASS * LENGTH


def test_quantity_derivative_second_order():
    engine = MathEngine()
    engine.set_lines([
        "x = 5 * m",
    ])

    result = engine.differentiate("x**3", "x", order=2)

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(30)
    assert result.dimension == LENGTH


def test_quantity_derivative_user_function():
    engine = MathEngine()
    engine.set_lines([
        "x = 5 * m",
        "f(t) = t**2",
    ])

    result = engine.differentiate("f(x)", "x")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(10)
    assert result.dimension == LENGTH


def test_derivative_does_not_change_variables():
    engine = MathEngine()
    engine.set_lines([
        "x = 5 * m",
    ])

    engine.differentiate("x**2", "x")

    result = engine.get_variable("x")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(5)
    assert result.dimension == LENGTH

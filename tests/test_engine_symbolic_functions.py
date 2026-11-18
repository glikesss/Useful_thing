import sympy as sp
import pytest

from core import MathEngine
from core.errors import DimensionError
from units.dimensions import DIMENSIONLESS, LENGTH, TIME
from units.quantities import SymbolicQuantity


def test_symbolic_function_preserves_dimensions():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.lines = [
        "f(x) = x**2",
    ]
    engine._rebuild()

    result = engine.call("f", engine.variables.get("x"))

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == LENGTH**2
    assert result.expression == sp.Symbol("x")**2


def test_symbolic_function_with_two_arguments():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.set_symbolic_variable("t", "t", TIME)
    engine.lines = [
        "f(x, t) = x / t",
    ]
    engine._rebuild()

    result = engine.call(
        "f",
        engine.variables.get("x"),
        engine.variables.get("t"),
    )

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == LENGTH / TIME


def test_symbolic_function_rejects_incompatible_addition():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.set_symbolic_variable("t", "t", TIME)
    engine.lines = [
        "f(x, t) = x + t",
    ]
    engine._rebuild()

    with pytest.raises(DimensionError):
        engine.call(
            "f",
            engine.variables.get("x"),
            engine.variables.get("t"),
        )


def test_symbolic_trigonometric_function():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", DIMENSIONLESS)

    result = engine.evaluate("sin(x)")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension.is_dimensionless
    assert result.expression == sp.sin(sp.Symbol("x"))


def test_trigonometric_function_rejects_dimensioned_argument():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)

    with pytest.raises(DimensionError):
        engine.evaluate("sin(x)")


def test_symbolic_sqrt_preserves_fractional_dimension():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)

    result = engine.evaluate("sqrt(x)")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == LENGTH ** sp.Rational(1, 2)


def test_symbolic_abs_preserves_dimension():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)

    result = engine.evaluate("abs(x)")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == LENGTH


def test_exp_rejects_dimensioned_argument():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", TIME)

    with pytest.raises(DimensionError):
        engine.evaluate("exp(x)")



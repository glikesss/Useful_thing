import sympy as sp
import pytest

from core import MathEngine
from core.errors import DimensionError
from units.dimensions import LENGTH, TIME
from units.quantities import SymbolicQuantity


def test_nested_symbolic_functions():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.lines = [
        "f(x) = x**2",
        "g(x) = f(x) + x**2",
    ]
    engine._rebuild()

    result = engine.call("g", engine.variables.get("x"))

    assert isinstance(result, SymbolicQuantity)
    assert result.expression == 2 * sp.Symbol("x")**2
    assert result.dimension == LENGTH**2


def test_nested_symbolic_functions_with_different_dimensions():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.set_symbolic_variable("t", "t", TIME)
    engine.lines = [
        "f(x, t) = x / t",
        "g(x, t) = f(x, t)**2",
    ]
    engine._rebuild()

    result = engine.call(
        "g",
        engine.variables.get("x"),
        engine.variables.get("t"),
    )

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == (LENGTH / TIME)**2


def test_nested_symbolic_function_dimension_mismatch():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.set_symbolic_variable("t", "t", TIME)
    engine.lines = [
        "f(x) = x**2",
        "g(x, t) = f(x) + t",
    ]
    engine._rebuild()

    with pytest.raises(DimensionError):
        engine.call(
            "g",
            engine.variables.get("x"),
            engine.variables.get("t"),
        )

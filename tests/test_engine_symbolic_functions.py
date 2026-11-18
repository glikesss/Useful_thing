import sympy as sp
import pytest

from core import MathEngine
from core.errors import DimensionError
from units.dimensions import LENGTH, TIME
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

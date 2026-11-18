import sympy as sp
import pytest

from core import MathEngine
from core.errors import DimensionError
from units.dimensions import LENGTH, TIME
from units.quantities import SymbolicQuantity


def test_evaluate_symbolic_quantity():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)

    result = engine.evaluate("2*x")

    assert isinstance(result, SymbolicQuantity)
    assert result.expression == 2 * sp.Symbol("x")
    assert result.dimension == LENGTH


def test_evaluate_sum_of_symbolic_quantities():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.set_symbolic_variable("y", "y", LENGTH)

    result = engine.evaluate("x + y")

    assert isinstance(result, SymbolicQuantity)
    assert result.expression == sp.Symbol("x") + sp.Symbol("y")
    assert result.dimension == LENGTH


def test_evaluate_dimension_mismatch():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.set_symbolic_variable("t", "t", TIME)

    with pytest.raises(DimensionError):
        engine.evaluate("x + t")

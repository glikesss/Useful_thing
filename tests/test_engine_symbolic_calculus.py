import sympy as sp

from core import MathEngine
from units.dimensions import LENGTH, TIME
from units.quantities import SymbolicQuantity


def test_differentiate_symbolic_quantity():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)

    result = engine.differentiate("x**2", "x")

    assert isinstance(result, SymbolicQuantity)
    assert result.expression == 2 * sp.Symbol("x")
    assert result.dimension == LENGTH


def test_integrate_symbolic_quantity():
    engine = MathEngine()
    engine.set_symbolic_variable("t", "t", TIME)

    result = engine.integrate("3*t", variable="t")

    assert isinstance(result, SymbolicQuantity)
    assert result.expression == sp.Rational(3, 2) * sp.Symbol("t")**2
    assert result.dimension == TIME**2


def test_definite_integrate_symbolic_quantity():
    engine = MathEngine()
    engine.set_symbolic_variable("t", "t", TIME)

    result = engine.integrate("t", variable="t", lower=0, upper=2)

    assert isinstance(result, SymbolicQuantity)
    assert result.expression == 2
    assert result.dimension == TIME**2
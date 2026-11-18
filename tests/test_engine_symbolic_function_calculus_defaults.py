import sympy as sp

from core import MathEngine
from units.dimensions import LENGTH, TIME
from units.quantities import SymbolicQuantity


def test_differentiate_function_with_default_argument():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.lines = [
        "f(x, k=2) = k*x**2",
    ]
    engine._rebuild()

    result = engine.differentiate("f(x)", "x")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == LENGTH
    assert sp.simplify(
        result.expression - 4 * sp.Symbol("x")
    ) == 0


def test_differentiate_function_with_overridden_argument():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.lines = [
        "f(x, k=2) = k*x**2",
    ]
    engine._rebuild()

    result = engine.differentiate("f(x, 3)", "x")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == LENGTH
    assert sp.simplify(
        result.expression - 6 * sp.Symbol("x")
    ) == 0


def test_integrate_function_with_default_argument():
    engine = MathEngine()
    engine.set_symbolic_variable("t", "t", TIME)
    engine.lines = [
        "f(t, k=2) = k*t",
    ]
    engine._rebuild()

    result = engine.integrate("f(t)", variable="t")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == TIME**2
    assert sp.simplify(
        result.expression - sp.Symbol("t")**2
    ) == 0


def test_integrate_function_with_overridden_argument():
    engine = MathEngine()
    engine.set_symbolic_variable("t", "t", TIME)
    engine.lines = [
        "f(t, k=2) = k*t",
    ]
    engine._rebuild()

    result = engine.integrate("f(t, 3)", variable="t")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == TIME**2
    assert sp.simplify(
        result.expression - sp.Rational(3, 2) * sp.Symbol("t")**2
    ) == 0

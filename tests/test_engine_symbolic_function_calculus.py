import sympy as sp

from core import MathEngine
from units.dimensions import LENGTH, TIME
from units.quantities import SymbolicQuantity


def test_differentiate_symbolic_user_function():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.lines = [
        "f(x) = x**2",
    ]
    engine._rebuild()

    result = engine.differentiate("f(x)", "x")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == LENGTH
    assert sp.simplify(result.expression - 2 * sp.Symbol("x")) == 0


def test_integrate_symbolic_user_function():
    engine = MathEngine()
    engine.set_symbolic_variable("t", "t", TIME)
    engine.lines = [
        "f(t) = 3*t",
    ]
    engine._rebuild()

    result = engine.integrate("f(t)", variable="t")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == TIME**2
    assert sp.simplify(result.expression - sp.Rational(3, 2) * sp.Symbol("t")**2) == 0


def test_differentiate_nested_symbolic_function():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.lines = [
        "f(x) = x**2",
        "g(x) = f(x)**2",
    ]
    engine._rebuild()

    result = engine.differentiate("g(x)", "x")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == LENGTH**3
    assert sp.simplify(result.expression - 4 * sp.Symbol("x")**3) == 0


def test_integrate_symbolic_function_with_global_variable():
    engine = MathEngine()
    engine.set_symbolic_variable("t", "t", TIME)
    engine.set_symbolic_variable("a", "a", LENGTH)
    engine.lines = [
        "f(t) = a*t",
    ]
    engine._rebuild()

    result = engine.integrate("f(t)", variable="t")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == LENGTH * TIME**2
    assert sp.simplify(
        result.expression - sp.Symbol("a") * sp.Symbol("t")**2 / 2
    ) == 0

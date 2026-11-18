import pytest
import sympy as sp

from core import MathEngine
from units.dimensions import LENGTH, TIME
from units.quantities import Quantity, SymbolicQuantity


def make_engine():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.set_symbolic_variable("t", "t", TIME)
    engine.lines = [
        "square(x) = x**2",
        "double(x) = 2*x",
        "nested(x) = square(x) + x**2",
    ]
    engine._rebuild()
    return engine


def test_unknown_function_raises_error():
    engine = make_engine()

    with pytest.raises(Exception):
        engine.call("unknown_function", 2)


def test_wrong_number_of_arguments_raises_error():
    engine = make_engine()

    with pytest.raises(Exception):
        engine.call("square")

    with pytest.raises(Exception):
        engine.call("square", 2, 3)


def test_function_with_undefined_global_variable():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.lines = [
        "f(x) = x + undefined_value",
    ]
    engine._rebuild()

    with pytest.raises(Exception):
        engine.call("f", engine.variables.get("x"))


def test_direct_recursive_function_is_rejected():
    engine = MathEngine()
    engine.lines = [
        "f(x) = f(x) + 1",
    ]

    with pytest.raises(Exception):
        engine._rebuild()


def test_indirect_recursive_functions_are_rejected():
    engine = MathEngine()
    engine.lines = [
        "f(x) = g(x) + 1",
        "g(x) = f(x) + 1",
    ]

    with pytest.raises(Exception):
        engine._rebuild()


def test_invalid_default_argument_is_rejected():
    engine = MathEngine()
    engine.lines = [
        "f(x, k=unknown_value) = x*k",
    ]

    with pytest.raises(Exception):
        engine._rebuild()


def test_engine_recovers_after_failed_call():
    engine = make_engine()

    with pytest.raises(Exception):
        engine.call("missing_function", 2)

    result = engine.call("double", 3)

    assert result == 6


def test_engine_recovers_after_dimension_error():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)
    engine.set_symbolic_variable("t", "t", TIME)
    engine.lines = [
        "bad(x, t) = x + t",
        "good(x) = x**2",
    ]
    engine._rebuild()

    with pytest.raises(Exception):
        engine.call(
            "bad",
            engine.variables.get("x"),
            engine.variables.get("t"),
        )

    result = engine.call("good", engine.variables.get("x"))

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == LENGTH**2


def test_numeric_nested_function_chain():
    engine = MathEngine()
    engine.lines = [
        "f(x) = x**2",
        "g(x) = f(x) + x**2",
        "h(x) = g(x)*x",
    ]
    engine._rebuild()

    assert engine.call("h", 2) == 16


def test_quantity_nested_function_chain():
    engine = MathEngine()
    engine.lines = [
        "f(x) = x**2",
        "g(x) = f(x) + x**2",
    ]
    engine._rebuild()

    value = Quantity(3, LENGTH)
    result = engine.call("g", value)

    assert isinstance(result, Quantity)
    assert result.dimension == LENGTH**2
    assert result.value == 18

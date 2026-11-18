import numpy as np
import pytest

from core import MathEngine
from core.errors import (
    EvaluationError,
    DependencyError,
)


def test_variables():
    engine = MathEngine()

    engine.set_lines([
        "a = 2.5",
        "b = a * 2",
    ])

    assert engine.get_variable("a") == 2.5
    assert engine.get_variable("b") == 5.0


def test_forward_variable_dependency():
    engine = MathEngine()

    engine.set_lines([
        "b = a * 2",
        "a = 3",
    ])

    assert engine.get_variable("b") == 6.0


def test_user_function():
    engine = MathEngine()

    engine.set_lines([
        "a = 2.5",
        "f(x) = a + x",
    ])

    assert engine.call("f", 3) == 5.5


def test_function_composition():
    engine = MathEngine()

    engine.set_lines([
        "a = 2.5",
        "f(x) = a + x",
        "g(x) = f(x)^2",
    ])

    assert engine.call("g", 2) == pytest.approx(20.25)


def test_default_arguments():
    engine = MathEngine()

    engine.set_lines([
        "f(x, a=2) = a*x",
    ])

    assert engine.call("f", 3) == 6
    assert engine.call("f", 3, 5) == 15


def test_numpy_arrays():
    engine = MathEngine()

    engine.set_lines([
        "f(x) = x^2",
    ])

    values = engine.call(
        "f",
        np.array([1, 2, 3, 4])
    )

    assert np.array_equal(
        values,
        np.array([1, 4, 9, 16])
    )


def test_math_functions():
    engine = MathEngine()

    assert engine.evaluate("sin(pi/2)") == pytest.approx(1.0)
    assert engine.evaluate("sqrt(16)") == pytest.approx(4.0)
    assert engine.evaluate("ln(e)") == pytest.approx(1.0)


def test_cycle_detection():
    engine = MathEngine()

    with pytest.raises(DependencyError):
        engine.set_lines([
            "a = b + 1",
            "b = a + 1",
        ])


def test_unknown_variable():
    engine = MathEngine()

    with pytest.raises(EvaluationError):
        engine.set_lines([
            "a = unknown + 1",
        ])


def test_update_line():
    engine = MathEngine()

    engine.set_lines([
        "a = 2",
        "b = a + 1",
    ])

    engine.update_line(0, "a = 10")

    assert engine.get_variable("b") == 11


def test_remove_line():
    engine = MathEngine()

    engine.set_lines([
        "a = 2",
        "b = 3",
    ])

    engine.remove_line(0)

    assert engine.get_variable("b") == 3
    assert engine.get_variable_names() == ("b",)
import numpy as np
import sympy as sp
import pytest

from core import MathEngine
from core.errors import ParseError


def test_first_derivative():
    engine = MathEngine()

    result = engine.differentiate("x^3", "x")
    x = sp.Symbol("x")

    assert sp.simplify(result - 3*x**2) == 0


def test_second_derivative():
    engine = MathEngine()

    result = engine.differentiate("x^4", "x", 2)
    x = sp.Symbol("x")

    assert sp.simplify(result - 12*x**2) == 0


def test_indefinite_integral():
    engine = MathEngine()

    result = engine.integrate("x^2", "x")
    x = sp.Symbol("x")

    assert sp.simplify(result - x**3 / 3) == 0


def test_definite_integral():
    engine = MathEngine()

    result = engine.integrate("x^2", "x", 0, 3)

    assert result == pytest.approx(9.0)


def test_derivative_of_user_function():
    engine = MathEngine()

    engine.set_lines([
        "f(x) = x^3",
        "df(x) = derivative(f(x), x)",
    ])

    assert engine.call("df", 2) == pytest.approx(12.0)


def test_second_derivative_in_formula():
    engine = MathEngine()

    engine.set_lines([
        "f(x) = x^4",
        "ddf(x) = derivative(f(x), x, 2)",
    ])

    assert engine.call("ddf", 2) == pytest.approx(48.0)


def test_integral_in_formula():
    engine = MathEngine()

    engine.set_lines([
        "f(x) = x^2",
        "F(x) = integral(f(x), x)",
    ])

    assert engine.call("F", 3) == pytest.approx(9.0)


def test_cumulative_symbolic():
    engine = MathEngine()

    engine.set_lines([
        "f(x) = x^2",
        "F(x) = cumulative(f(x), x, 0)",
    ])

    assert engine.call("F", 3) == pytest.approx(9.0)


def test_numerical_cumulative():
    engine = MathEngine()

    values = np.array([0, 1, 2, 3], dtype=float)

    result = engine.cumulative(
        "2*x",
        values,
        start=0,
    )

    expected = np.array([0, 1, 4, 9], dtype=float)

    assert np.allclose(result, expected)


def test_empty_cumulative():
    engine = MathEngine()

    result = engine.cumulative(
        "x",
        np.array([]),
    )

    assert len(result) == 0


def test_invalid_derivative_order():
    engine = MathEngine()

    with pytest.raises(ParseError):
        engine.differentiate("x^2", "x", 0)
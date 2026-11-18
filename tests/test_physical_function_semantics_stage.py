
import math

import numpy as np
import pytest
import sympy as sp

from core import MathEngine
from core.errors import DimensionError, EvaluationError
from units.dimensions import (
    DIMENSIONLESS,
    LENGTH,
    TIME,
    AREA,
)
from units.quantities import Quantity, SymbolicQuantity
from units.expression import QuantityExpressionEvaluator
from units.registry import get_unit
from units.conversion import convert_value


# ============================================================
# ANGLES AND TRIGONOMETRY
# ============================================================

def test_radian_unit_is_dimensionless():
    assert get_unit("rad").dimension == DIMENSIONLESS
    assert get_unit("radian").dimension == DIMENSIONLESS


def test_degree_unit_is_dimensionless():
    assert get_unit("deg").dimension == DIMENSIONLESS
    assert get_unit("degree").dimension == DIMENSIONLESS


def test_degree_scale_to_radians():
    assert get_unit("deg").scale_to_si == pytest.approx(math.pi / 180)


def test_radian_scale():
    assert get_unit("rad").scale_to_si == pytest.approx(1)


def test_convert_degrees_to_radians():
    result = convert_value(
        180,
        get_unit("deg"),
        get_unit("rad"),
    )
    assert result == pytest.approx(math.pi)


def test_convert_radians_to_degrees():
    result = convert_value(
        math.pi,
        get_unit("rad"),
        get_unit("deg"),
    )
    assert result == pytest.approx(180)


def test_sin_accepts_degrees():
    result = QuantityExpressionEvaluator().evaluate("sin(90 * deg)")
    assert result == pytest.approx(1)


def test_cos_accepts_degrees():
    result = QuantityExpressionEvaluator().evaluate("cos(180 * deg)")
    assert result == pytest.approx(-1)


def test_sin_accepts_radians():
    result = QuantityExpressionEvaluator().evaluate("sin(pi / 2 * rad)")
    assert result == pytest.approx(1)


def test_trigonometry_rejects_length():
    evaluator = QuantityExpressionEvaluator({
        "x": Quantity(2, LENGTH),
    })

    with pytest.raises(ValueError, match="dimensionless"):
        evaluator.evaluate("sin(x)")


# ============================================================
# DIMENSIONLESS MATHEMATICAL FUNCTIONS
# ============================================================

@pytest.mark.parametrize(
    "function",
    [
        "sin", "cos", "tan",
        "asin", "acos", "atan",
        "sinh", "cosh", "tanh",
        "exp", "ln", "log", "log10",
    ],
)
def test_math_functions_reject_dimensioned_arguments(function):
    evaluator = QuantityExpressionEvaluator({
        "x": Quantity(0.5, LENGTH),
    })

    with pytest.raises(ValueError, match="dimensionless"):
        evaluator.evaluate(f"{function}(x)")


def test_exp_accepts_dimensionless_quantity():
    evaluator = QuantityExpressionEvaluator({
        "x": Quantity(1, DIMENSIONLESS),
    })

    assert evaluator.evaluate("exp(x)") == pytest.approx(math.e)


def test_ln_accepts_dimensionless_quantity():
    evaluator = QuantityExpressionEvaluator({
        "x": Quantity(math.e, DIMENSIONLESS),
    })

    assert evaluator.evaluate("ln(x)") == pytest.approx(1)


def test_log10_accepts_dimensionless_quantity():
    evaluator = QuantityExpressionEvaluator({
        "x": Quantity(100, DIMENSIONLESS),
    })

    assert evaluator.evaluate("log10(x)") == pytest.approx(2)


def test_sin_accepts_dimensionless_quantity():
    evaluator = QuantityExpressionEvaluator({
        "x": Quantity(math.pi / 2, DIMENSIONLESS),
    })

    assert evaluator.evaluate("sin(x)") == pytest.approx(1)


# ============================================================
# DIMENSIONED SQRT AND ABS
# ============================================================

def test_sqrt_of_length_has_fractional_dimension():
    result = QuantityExpressionEvaluator().evaluate("sqrt(9 * m)")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(3)
    assert result.dimension == LENGTH ** 0.5


def test_sqrt_of_area_has_length_dimension():
    result = QuantityExpressionEvaluator().evaluate("sqrt(9 * m**2)")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(3)
    assert result.dimension == LENGTH


def test_sqrt_of_dimensioned_array():
    evaluator = QuantityExpressionEvaluator({
        "area": Quantity(np.array([1, 4, 9]), AREA),
    })

    result = evaluator.evaluate("sqrt(area)")

    assert isinstance(result, Quantity)
    assert np.allclose(result.value, [1, 2, 3])
    assert result.dimension == LENGTH


def test_abs_preserves_dimension():
    result = QuantityExpressionEvaluator().evaluate("abs(-3 * m)")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(3)
    assert result.dimension == LENGTH


def test_abs_preserves_array_dimension():
    evaluator = QuantityExpressionEvaluator({
        "x": Quantity(np.array([-1, 2, -3]), LENGTH),
    })

    result = evaluator.evaluate("abs(x)")

    assert isinstance(result, Quantity)
    assert np.allclose(result.value, [1, 2, 3])
    assert result.dimension == LENGTH


# ============================================================
# SYMBOLIC MATHEMATICAL FUNCTIONS
# ============================================================

def test_symbolic_sqrt_preserves_fractional_dimension():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)

    result = engine.evaluate("sqrt(x)")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == LENGTH ** 0.5
    assert result.expression == sp.sqrt(sp.Symbol("x"))


def test_symbolic_sqrt_of_area_has_length_dimension():
    engine = MathEngine()
    engine.set_symbolic_variable("area", "area", AREA)

    result = engine.evaluate("sqrt(area)")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == LENGTH


def test_symbolic_abs_preserves_dimension():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)

    result = engine.evaluate("abs(x)")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == LENGTH


def test_symbolic_trigonometry_accepts_dimensionless_argument():
    engine = MathEngine()
    engine.set_symbolic_variable("theta", "theta", DIMENSIONLESS)

    result = engine.evaluate("sin(theta)")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == DIMENSIONLESS
    assert result.expression == sp.sin(sp.Symbol("theta"))


def test_symbolic_trigonometry_rejects_length():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)

    with pytest.raises(DimensionError):
        engine.evaluate("sin(x)")


def test_symbolic_log_rejects_dimensioned_argument():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)

    with pytest.raises(DimensionError):
        engine.evaluate("ln(x)")


# ============================================================
# USER-DEFINED FUNCTIONS
# ============================================================

def make_function_engine():
    engine = MathEngine()
    engine.set_lines([
        "square(x) = x**2",
        "root(x) = sqrt(x)",
        "sine(x) = sin(x)",
        "invalid(x) = x + 1",
    ])
    return engine


def test_user_function_preserves_dimension():
    engine = make_function_engine()

    result = engine.call("square", Quantity(3, LENGTH))

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(9)
    assert result.dimension == AREA


def test_user_function_sqrt_preserves_dimension():
    engine = make_function_engine()

    result = engine.call("root", Quantity(9, AREA))

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(3)
    assert result.dimension == LENGTH


def test_user_function_rejects_dimensioned_trigonometry():
    engine = make_function_engine()

    with pytest.raises(ValueError, match="dimensionless"):
        engine.call("sine", Quantity(2, LENGTH))


def test_user_function_accepts_angle_in_degrees():
    engine = make_function_engine()

    result = engine.evaluate("sine(90 * deg)")

    assert result == pytest.approx(1)


def test_user_function_rejects_incompatible_addition():
    engine = make_function_engine()

    with pytest.raises(DimensionError):
        engine.call("invalid", Quantity(2, LENGTH))


# ============================================================
# DIMENSIONAL DIFFERENTIATION
# ============================================================

def test_first_derivative_has_correct_dimension():
    engine = MathEngine()
    engine.set_lines(["x = 2 * m"])

    result = engine.differentiate("x**3", "x")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(12)
    assert result.dimension == AREA


def test_second_derivative_has_correct_dimension():
    engine = MathEngine()
    engine.set_lines(["x = 2 * m"])

    result = engine.differentiate("x**3", "x", order=2)

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(12)
    assert result.dimension == LENGTH


def test_symbolic_derivative_has_correct_dimension():
    engine = MathEngine()
    engine.set_symbolic_variable("x", "x", LENGTH)

    result = engine.differentiate("x**3", "x")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == AREA


def test_derivative_rejects_dimensioned_trigonometry():
    engine = MathEngine()
    engine.set_lines(["x = 2 * m"])

    with pytest.raises(EvaluationError):
        engine.differentiate("sin(x)", "x")


# ============================================================
# DIMENSIONAL INTEGRATION
# ============================================================

def test_integral_of_time_dependent_acceleration():
    engine = MathEngine()
    engine.set_lines(["a = 2 * m / s**2"])

    result = engine.integrate(
        "a * t",
        variable="t",
        lower=Quantity(0, TIME),
        upper=Quantity(2, TIME),
    )

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(4)
    assert result.dimension == LENGTH


def test_symbolic_integral_has_correct_dimension():
    engine = MathEngine()
    engine.set_symbolic_variable("t", "t", TIME)

    result = engine.integrate("3 * t", variable="t")

    assert isinstance(result, SymbolicQuantity)
    assert result.dimension == TIME ** 2


def test_cumulative_integral_preserves_dimensions():
    engine = MathEngine()
    engine.set_lines(["a = 2 * m / s**2"])

    result = engine.cumulative(
        "a * t",
        values=[
            Quantity(1, TIME),
            Quantity(2, TIME),
            Quantity(3, TIME),
        ],
        variable="t",
        start=Quantity(0, TIME),
    )

    assert isinstance(result, Quantity)
    assert result.dimension == LENGTH
    assert np.allclose(result.value, [1, 4, 9])


def test_integral_rejects_incompatible_limits():
    engine = MathEngine()

    with pytest.raises(DimensionError):
        engine.integrate(
            "3 * m / s",
            variable="t",
            lower=Quantity(0, TIME),
            upper=Quantity(2, LENGTH),
        )

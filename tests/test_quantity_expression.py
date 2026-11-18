
import pytest

from units.expression import QuantityExpressionEvaluator
from units.quantities import Quantity
from units.dimensions import LENGTH, MASS, TIME, FORCE

from core.errors import DimensionError


def test_simple_quantity():
    evaluator = QuantityExpressionEvaluator()

    result = evaluator.evaluate("2 * kg")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(2)
    assert result.dimension == MASS


def test_unit_conversion_to_si():
    evaluator = QuantityExpressionEvaluator()

    result = evaluator.evaluate("100 * cm")

    assert result.value == pytest.approx(1)
    assert result.dimension == LENGTH


def test_compound_unit():
    evaluator = QuantityExpressionEvaluator()

    result = evaluator.evaluate("9.81 * m / s**2")

    assert result.dimension == LENGTH / (TIME ** 2)
    assert result.value == pytest.approx(9.81)


def test_force_calculation():
    evaluator = QuantityExpressionEvaluator({
        "mass": evaluator_quantity(2, MASS),
        "acceleration": evaluator_quantity(9.81, LENGTH / (TIME ** 2)),
    })

    result = evaluator.evaluate("mass * acceleration")

    assert result.dimension == FORCE
    assert result.value == pytest.approx(19.62)


def test_dimension_mismatch():
    evaluator = QuantityExpressionEvaluator()

    with pytest.raises(DimensionError):
        evaluator.evaluate("2 * kg + 3 * m")


def test_power():
    evaluator = QuantityExpressionEvaluator()

    result = evaluator.evaluate("(3 * m)**2")

    assert result.value == pytest.approx(9)
    assert result.dimension == LENGTH ** 2


def test_trigonometry():
    evaluator = QuantityExpressionEvaluator()

    result = evaluator.evaluate("sin(pi / 2)")

    assert result == pytest.approx(1)


def test_dimensionless_quantity_function():
    evaluator = QuantityExpressionEvaluator()

    result = evaluator.evaluate("sqrt(4 * m / m)")

    assert result == pytest.approx(2)


def evaluator_quantity(value, dimension):
    return Quantity(value, dimension)

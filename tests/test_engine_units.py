
import pytest

from core import MathEngine
from core.errors import DimensionError
from units.quantities import Quantity
from units.dimensions import LENGTH, MASS, FORCE, TIME


def test_quantity_variable():
    engine = MathEngine()
    engine.set_lines([
        "mass = 2 * kg",
    ])

    result = engine.get_variable("mass")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(2)
    assert result.dimension == MASS


def test_quantity_dependencies():
    engine = MathEngine()
    engine.set_lines([
        "mass = 2 * kg",
        "acceleration = 9.81 * m / s**2",
        "force = mass * acceleration",
    ])

    result = engine.get_variable("force")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(19.62)
    assert result.dimension == FORCE


def test_quantity_forward_dependency():
    engine = MathEngine()
    engine.set_lines([
        "force = mass * acceleration",
        "acceleration = 9.81 * m / s**2",
        "mass = 2 * kg",
    ])

    assert engine.get_variable("force").value == pytest.approx(19.62)


def test_quantity_expression_evaluate():
    engine = MathEngine()
    engine.set_lines([
        "mass = 2 * kg",
        "acceleration = 9.81 * m / s**2",
    ])

    result = engine.evaluate("mass * acceleration")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(19.62)
    assert result.dimension == FORCE


def test_quantity_dimension_mismatch():
    engine = MathEngine()

    with pytest.raises(DimensionError):
        engine.set_lines([
            "mass = 2 * kg",
            "length = 3 * m",
            "invalid = mass + length",
        ])


def test_quantity_conversion_base_units():
    engine = MathEngine()
    engine.set_lines([
        "length = 100 * cm",
    ])

    result = engine.get_variable("length")

    assert result.value == pytest.approx(1)
    assert result.dimension == LENGTH


def test_ordinary_variables_still_work():
    engine = MathEngine()
    engine.set_lines([
        "a = 2",
        "b = a * 3",
    ])

    assert engine.get_variable("a") == 2
    assert engine.get_variable("b") == 6


def test_quantity_evaluate_arithmetic():
    engine = MathEngine()
    engine.set_lines([
        "length = 5 * m",
    ])

    result = engine.evaluate("length / (2 * s)")

    assert result.dimension == LENGTH / TIME
    assert result.value == pytest.approx(2.5)

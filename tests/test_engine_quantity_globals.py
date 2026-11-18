
import pytest

from core import MathEngine
from units.quantities import Quantity
from units.dimensions import MASS, FORCE, LENGTH


def test_function_uses_global_quantity_with_numeric_argument():
    engine = MathEngine()
    engine.set_lines([
        "mass = 2 * kg",
        "F(a) = mass * a",
    ])

    result = engine.call("F", 3)

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(6)
    assert result.dimension == MASS


def test_function_uses_global_quantity_in_expression():
    engine = MathEngine()
    engine.set_lines([
        "mass = 2 * kg",
        "F(a) = mass * a",
    ])

    result = engine.evaluate("F(3)")

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(6)
    assert result.dimension == MASS


def test_nested_function_uses_global_quantity():
    engine = MathEngine()
    engine.set_lines([
        "mass = 2 * kg",
        "F(a) = mass * a",
        "G(a) = F(a) * 2",
    ])

    result = engine.call("G", 3)

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(12)
    assert result.dimension == MASS


def test_function_global_quantity_dependency_updates():
    engine = MathEngine()
    engine.set_lines([
        "mass = 2 * kg",
        "F(a) = mass * a",
    ])

    first = engine.call("F", 3)

    engine.set_lines([
        "mass = 5 * kg",
        "F(a) = mass * a",
    ])

    second = engine.call("F", 3)

    assert first.value == pytest.approx(6)
    assert second.value == pytest.approx(15)


def test_function_with_global_quantity_and_quantity_argument():
    engine = MathEngine()
    engine.set_lines([
        "mass = 2 * kg",
        "F(a) = mass * a",
    ])

    result = engine.call("F", Quantity(3, LENGTH))

    assert isinstance(result, Quantity)
    assert result.value == pytest.approx(6)
    assert result.dimension == MASS * LENGTH


def test_ordinary_function_without_quantity_still_works():
    engine = MathEngine()
    engine.set_lines([
        "a = 10",
        "f(x) = x**2 + a",
    ])

    assert engine.call("f", 3) == pytest.approx(19)

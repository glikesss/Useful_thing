import sympy as sp
import pytest

from core.errors import DimensionError
from units.dimensions import (
    DIMENSIONLESS,
    LENGTH,
    MASS,
    TIME,
)
from units.quantities import SymbolicQuantity


x = sp.Symbol("x")
y = sp.Symbol("y")


def test_creation():
    quantity = SymbolicQuantity(3 * x, LENGTH)

    assert quantity.expression == 3 * x
    assert quantity.dimension == LENGTH


def test_creation_from_number():
    quantity = SymbolicQuantity(5, MASS)

    assert quantity.expression == sp.Integer(5)
    assert quantity.dimension == MASS


def test_addition():
    a = SymbolicQuantity(2 * x, LENGTH)
    b = SymbolicQuantity(3 * x, LENGTH)

    result = a + b

    assert result.expression == 5 * x
    assert result.dimension == LENGTH


def test_addition_dimension_mismatch():
    a = SymbolicQuantity(x, LENGTH)
    b = SymbolicQuantity(x, TIME)

    with pytest.raises(DimensionError):
        a + b


def test_subtraction():
    a = SymbolicQuantity(5 * x, LENGTH)
    b = SymbolicQuantity(2 * x, LENGTH)

    result = a - b

    assert result.expression == 3 * x
    assert result.dimension == LENGTH


def test_multiplication():
    a = SymbolicQuantity(2 * x, LENGTH)
    b = SymbolicQuantity(3 * y, TIME)

    result = a * b

    assert result.expression == 6 * x * y
    assert result.dimension == LENGTH * TIME


def test_division():
    a = SymbolicQuantity(6 * x, LENGTH)
    b = SymbolicQuantity(2 * y, TIME)

    result = a / b

    assert result.expression == 3 * x / y
    assert result.dimension == LENGTH / TIME


def test_scalar_multiplication():
    quantity = SymbolicQuantity(x, LENGTH)

    result = quantity * 3

    assert result.expression == 3 * x
    assert result.dimension == LENGTH


def test_scalar_division():
    quantity = SymbolicQuantity(6 * x, LENGTH)

    result = quantity / 2

    assert result.expression == 3 * x
    assert result.dimension == LENGTH


def test_power():
    quantity = SymbolicQuantity(x, LENGTH)

    result = quantity ** 2

    assert result.expression == x**2
    assert result.dimension == LENGTH**2


def test_fractional_power():
    quantity = SymbolicQuantity(x, LENGTH)

    result = quantity ** sp.Rational(1, 2)

    assert result.expression == sp.sqrt(x)
    assert result.dimension == LENGTH ** sp.Rational(1, 2)


def test_dimensionless_power():
    quantity = SymbolicQuantity(x, DIMENSIONLESS)

    result = quantity ** y

    assert result.expression == x**y
    assert result.dimension == DIMENSIONLESS


def test_negation():
    quantity = SymbolicQuantity(x, LENGTH)

    result = -quantity

    assert result.expression == -x
    assert result.dimension == LENGTH


def test_differentiation():
    quantity = SymbolicQuantity(3 * x**2, LENGTH)

    result = quantity.diff(x)

    assert result.expression == 6 * x
    assert result.dimension == LENGTH


def test_substitution():
    quantity = SymbolicQuantity(3 * x**2, LENGTH)

    result = quantity.subs(x, 2)

    assert result.expression == 12
    assert result.dimension == LENGTH


def test_simplify():
    quantity = SymbolicQuantity(x + x, LENGTH)

    result = quantity.simplify()

    assert result.expression == 2 * x
    assert result.dimension == LENGTH


def test_equality():
    a = SymbolicQuantity(2 * x, LENGTH)
    b = SymbolicQuantity(x + x, LENGTH)

    assert a == b


def test_inequality_by_dimension():
    a = SymbolicQuantity(x, LENGTH)
    b = SymbolicQuantity(x, TIME)

    assert a != b
import sympy as sp
import pytest

from core.errors import DimensionError
from units.dimensions import (
    LENGTH,
    TIME,
    MASS,
)
from units.quantities import Quantity, SymbolicQuantity


t = sp.Symbol("t")


def test_indefinite_integration():
    quantity = SymbolicQuantity(3 * t, LENGTH)

    result = quantity.integrate(t, variable_dimension=TIME)

    assert result.expression == sp.Rational(3, 2) * t**2
    assert result.dimension == LENGTH * TIME


def test_integration_of_constant():
    quantity = SymbolicQuantity(5, LENGTH)

    result = quantity.integrate(t, variable_dimension=TIME)

    assert result.expression == 5 * t
    assert result.dimension == LENGTH * TIME


def test_definite_integration():
    quantity = SymbolicQuantity(3 * t, LENGTH)

    result = quantity.integrate(
        t,
        lower=0,
        upper=2,
        variable_dimension=TIME,
    )

    assert result.expression == 6
    assert result.dimension == LENGTH * TIME


def test_integration_without_variable_dimension():
    quantity = SymbolicQuantity(3 * t, LENGTH)

    with pytest.raises(ValueError):
        quantity.integrate(t)


def test_integration_dimension_mismatch():
    quantity = SymbolicQuantity(3 * t, LENGTH)

    with pytest.raises(DimensionError):
        quantity.integrate(
            t,
            lower=SymbolicQuantity(0, TIME),
            upper=SymbolicQuantity(2, MASS),
            variable_dimension=TIME,
        )


def test_integrate_then_differentiate():
    quantity = SymbolicQuantity(3 * t**2, MASS)

    integral = quantity.integrate(t, variable_dimension=TIME)
    derivative = integral.diff(t)

    assert sp.simplify(
        derivative.expression - quantity.expression
    ) == 0

    assert derivative.dimension == integral.dimension


def test_definite_integration_with_quantity_bounds():
    quantity = SymbolicQuantity(3 * t, LENGTH)

    result = quantity.integrate(
        t,
        lower=Quantity(0, TIME),
        upper=Quantity(2, TIME),
        variable_dimension=TIME,
    )

    assert result.expression == 6
    assert result.dimension == LENGTH * TIME


def test_quantity_bounds_dimension_mismatch():
    quantity = SymbolicQuantity(3 * t, LENGTH)

    with pytest.raises(DimensionError):
        quantity.integrate(
            t,
            lower=Quantity(0, TIME),
            upper=Quantity(2, MASS),
            variable_dimension=TIME,
        )


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


x, y, t = sp.symbols("x y t")


def test_symbol_dimensions():
    quantity = SymbolicQuantity(
        x + y,
        symbol_dimensions={
            x: LENGTH,
            y: LENGTH,
        },
    )

    assert quantity.dimension == LENGTH


def test_symbol_dimension_mismatch():
    with pytest.raises(DimensionError):
        SymbolicQuantity(
            x + t,
            symbol_dimensions={
                x: LENGTH,
                t: TIME,
            },
        )


def test_symbol_multiplication_dimensions():
    quantity = SymbolicQuantity(
        x * t,
        symbol_dimensions={
            x: LENGTH,
            t: TIME,
        },
    )

    assert quantity.dimension == LENGTH * TIME


def test_symbol_division_dimensions():
    quantity = SymbolicQuantity(
        x / t,
        symbol_dimensions={
            x: LENGTH,
            t: TIME,
        },
    )

    assert quantity.dimension == LENGTH / TIME


def test_symbol_power_dimensions():
    quantity = SymbolicQuantity(
        x**2,
        symbol_dimensions={
            x: LENGTH,
        },
    )

    assert quantity.dimension == LENGTH**2


def test_dimensionless_symbol():
    quantity = SymbolicQuantity(
        sp.sin(x),
        symbol_dimensions={
            x: DIMENSIONLESS,
        },
    )

    assert quantity.dimension == DIMENSIONLESS


def test_unknown_symbol_requires_dimension():
    with pytest.raises(DimensionError):
        SymbolicQuantity(
            x + y,
            symbol_dimensions={
                x: LENGTH,
            },
        )


def test_differentiate_symbolic_quantity():
    quantity = SymbolicQuantity(
        x**2,
        symbol_dimensions={
            x: LENGTH,
        },
    )

    result = quantity.diff(x)

    assert result.expression == 2 * x
    assert result.dimension == LENGTH


def test_differentiation_dimension():
    quantity = SymbolicQuantity(
        x**2,
        LENGTH**2,
        symbol_dimensions={
            x: LENGTH,
        },
    )

    result = quantity.diff(x)

    assert result.dimension == LENGTH


def test_integrate_symbolic_quantity():
    quantity = SymbolicQuantity(
        3 * t,
        LENGTH / TIME,
        symbol_dimensions={
            t: TIME,
        },
    )

    result = quantity.integrate(t)

    assert result.expression == sp.Rational(3, 2) * t**2
    assert result.dimension == LENGTH
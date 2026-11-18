import sympy as sp
import pytest

from core.errors import DimensionError
from units.dimensions import DIMENSIONLESS, LENGTH
from units.quantities import SymbolicQuantity


x = sp.Symbol("x")


@pytest.fixture
def q():
    return SymbolicQuantity(
        x,
        DIMENSIONLESS,
        {x: DIMENSIONLESS},
    )


def test_symbolic_plus_scalar(q):
    result = q + 1
    assert result.expression == x + 1
    assert result.dimension == DIMENSIONLESS


def test_scalar_plus_symbolic(q):
    result = 1 + q
    assert result.expression == x + 1
    assert result.dimension == DIMENSIONLESS


def test_symbolic_minus_scalar(q):
    result = q - 1
    assert result.expression == x - 1
    assert result.dimension == DIMENSIONLESS


def test_scalar_minus_symbolic(q):
    result = 1 - q
    assert result.expression == 1 - x
    assert result.dimension == DIMENSIONLESS


def test_dimensioned_symbolic_plus_scalar():
    q = SymbolicQuantity(x, LENGTH, {x: LENGTH})
    with pytest.raises(DimensionError):
        q + 1


def test_dimensioned_scalar_minus_symbolic():
    q = SymbolicQuantity(x, LENGTH, {x: LENGTH})
    with pytest.raises(DimensionError):
        1 - q

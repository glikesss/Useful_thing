
import pytest

from units.dimensions import (
    DIMENSIONLESS,
    LENGTH,
    MASS,
    TIME,
    VELOCITY,
    ACCELERATION,
    FORCE,
    ENERGY,
    POWER,
    CHARGE,
    Dimension,
)


def test_base_dimensions():
    assert LENGTH != MASS
    assert TIME != LENGTH
    assert DIMENSIONLESS.is_dimensionless


def test_multiplication():
    assert LENGTH * LENGTH == LENGTH ** 2


def test_division():
    assert LENGTH / TIME == VELOCITY


def test_power():
    assert LENGTH ** 2 == Dimension.from_mapping({"L": 2})


def test_fractional_power():
    assert LENGTH ** 0.5 == LENGTH ** 0.5


def test_derived_dimensions():
    assert FORCE == MASS * ACCELERATION
    assert ENERGY == FORCE * LENGTH
    assert POWER == ENERGY / TIME


def test_charge():
    assert CHARGE == Dimension.from_mapping({
        "I": 1,
        "T": 1,
    })


def test_dimensionless():
    assert (LENGTH / LENGTH).is_dimensionless


def test_invalid_base_dimension():
    with pytest.raises(ValueError):
        Dimension.base("X")


def test_invalid_number_of_exponents():
    with pytest.raises(ValueError):
        Dimension((1, 2, 3))


import numpy as np
import pytest

from core.errors import DimensionError

from units.dimensions import (
    DIMENSIONLESS,
    LENGTH,
    MASS,
    TIME,
    VELOCITY,
    FORCE,
    ENERGY,
)

from units.quantities import Quantity


def test_addition():
    a = Quantity(2, LENGTH)
    b = Quantity(3, LENGTH)

    result = a + b

    assert result.value == 5
    assert result.dimension == LENGTH


def test_subtraction():
    result = Quantity(5, LENGTH) - Quantity(2, LENGTH)

    assert result.value == 3


def test_incompatible_addition():
    with pytest.raises(DimensionError):
        Quantity(2, LENGTH) + Quantity(3, TIME)


def test_multiplication():
    result = Quantity(2, MASS) * Quantity(3, FORCE)

    assert result.value == 6
    assert result.dimension == MASS * FORCE


def test_division():
    result = Quantity(10, LENGTH) / Quantity(2, TIME)

    assert result.value == 5
    assert result.dimension == VELOCITY


def test_scalar_multiplication():
    result = Quantity(5, LENGTH) * 2

    assert result.value == 10
    assert result.dimension == LENGTH


def test_scalar_division():
    result = Quantity(10, LENGTH) / 2

    assert result.value == 5
    assert result.dimension == LENGTH


def test_power():
    result = Quantity(3, LENGTH) ** 2

    assert result.value == 9
    assert result.dimension == LENGTH ** 2


def test_fractional_power():
    result = Quantity(9, LENGTH ** 2) ** 0.5

    assert result.value == 3
    assert result.dimension == LENGTH


def test_dimensionless_power():
    result = Quantity(2, DIMENSIONLESS) ** 3

    assert result.value == 8
    assert result.dimension == DIMENSIONLESS


def test_comparison():
    assert Quantity(5, LENGTH) > Quantity(3, LENGTH)
    assert Quantity(5, LENGTH) == Quantity(5, LENGTH)


def test_incompatible_comparison():
    with pytest.raises(DimensionError):
        Quantity(5, LENGTH) > Quantity(3, TIME)


def test_numpy_arrays():
    values = Quantity(np.array([1, 2, 3]), LENGTH)
    result = values * 2

    np.testing.assert_array_equal(
        result.value,
        np.array([2, 4, 6]),
    )

    assert result.dimension == LENGTH


def test_force_calculation():
    mass = Quantity(2, MASS)
    acceleration = Quantity(9.81, LENGTH / TIME ** 2)

    force = mass * acceleration

    assert force.value == pytest.approx(19.62)
    assert force.dimension == FORCE


def test_energy_calculation():
    force = Quantity(10, FORCE)
    distance = Quantity(5, LENGTH)

    energy = force * distance

    assert energy.value == 50
    assert energy.dimension == ENERGY


def test_reverse_division():
    result = 1 / Quantity(2, TIME)

    assert result.value == 0.5
    assert result.dimension == DIMENSIONLESS / TIME


def test_negative():
    result = -Quantity(5, LENGTH)

    assert result.value == -5
    assert result.dimension == LENGTH

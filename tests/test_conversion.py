
import numpy as np
import pytest

from core.errors import DimensionError

from units.quantities import Quantity
from units.systems import SI, CGS_ESU, CGS_EMU

from units.conversion import convert_value, convert_quantity


def test_cm_to_m():
    result = convert_value(
        100,
        CGS_ESU.get_unit("centimeter"),
        SI.get_unit("meter"),
    )

    assert result == pytest.approx(1)


def test_m_to_cm():
    result = convert_value(
        2,
        SI.get_unit("meter"),
        CGS_ESU.get_unit("centimeter"),
    )

    assert result == pytest.approx(200)


def test_gram_to_kg():
    result = convert_value(
        1000,
        CGS_ESU.get_unit("gram"),
        SI.get_unit("kilogram"),
    )

    assert result == pytest.approx(1)


def test_erg_to_joule():
    result = convert_value(
        1e7,
        CGS_ESU.get_unit("erg"),
        SI.get_unit("joule"),
    )

    assert result == pytest.approx(1)


def test_dyne_to_newton():
    result = convert_value(
        1e5,
        CGS_ESU.get_unit("dyne"),
        SI.get_unit("newton"),
    )

    assert result == pytest.approx(1)


def test_statcoulomb_to_coulomb():
    result = convert_value(
        1,
        CGS_ESU.get_unit("statcoulomb"),
        SI.get_unit("coulomb"),
    )

    assert result == pytest.approx(3.3356409519815204e-10)


def test_gauss_to_tesla():
    result = convert_value(
        10000,
        CGS_EMU.get_unit("gauss"),
        SI.get_unit("tesla"),
    )

    assert result == pytest.approx(1)


def test_quantity_conversion():
    quantity = Quantity(
        150,
        SI.get_unit("meter").dimension,
    )

    result = convert_quantity(
        quantity,
        SI.get_unit("meter"),
        CGS_ESU.get_unit("centimeter"),
    )

    assert result.value == pytest.approx(15000)
    assert result.dimension == quantity.dimension


def test_array_conversion():
    values = np.array([1, 2, 3])

    result = convert_value(
        values,
        SI.get_unit("meter"),
        CGS_ESU.get_unit("centimeter"),
    )

    np.testing.assert_allclose(
        result,
        np.array([100, 200, 300]),
    )


def test_incompatible_units():
    with pytest.raises(DimensionError):
        convert_value(
            1,
            SI.get_unit("meter"),
            SI.get_unit("second"),
        )


def test_quantity_dimension_mismatch():
    quantity = Quantity(
        5,
        SI.get_unit("second").dimension,
    )

    with pytest.raises(DimensionError):
        convert_quantity(
            quantity,
            SI.get_unit("meter"),
            CGS_ESU.get_unit("centimeter"),
        )


def test_identity_conversion():
    result = convert_value(
        42,
        SI.get_unit("meter"),
        SI.get_unit("meter"),
    )

    assert result == pytest.approx(42)

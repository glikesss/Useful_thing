
import pytest

from units.registry import UNITS, get_unit, is_unit
from units.dimensions import LENGTH, MASS, TIME, FORCE


def test_si_aliases():
    assert get_unit("m").dimension == LENGTH
    assert get_unit("meter").dimension == LENGTH
    assert get_unit("kg").dimension == MASS
    assert get_unit("s").dimension == TIME


def test_derived_aliases():
    assert get_unit("N").dimension == FORCE
    assert get_unit("newton").dimension == FORCE


def test_cgs_aliases():
    assert get_unit("cm").dimension == LENGTH
    assert get_unit("g").dimension == MASS
    assert get_unit("dyn").dimension == FORCE


def test_unit_scale():
    assert get_unit("cm").scale_to_si == pytest.approx(0.01)
    assert get_unit("g").scale_to_si == pytest.approx(0.001)


def test_unit_detection():
    assert is_unit("kg")
    assert is_unit("meter")
    assert not is_unit("unknown")


def test_unknown_unit():
    with pytest.raises(KeyError):
        get_unit("unknown")


def test_registry_immutable():
    with pytest.raises(TypeError):
        UNITS["new_unit"] = get_unit("m")

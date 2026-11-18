
import pytest

from units.systems import (
    SI,
    CGS_ESU,
    CGS_EMU,
    GAUSSIAN,
    SYSTEMS,
    get_system,
)

from units.dimensions import (
    LENGTH,
    MASS,
    FORCE,
    ENERGY,
    CHARGE,
    VOLTAGE,
    MAGNETIC_FIELD,
)


def test_all_systems_registered():
    assert set(SYSTEMS) == {
        "SI",
        "CGS-ESU",
        "CGS-EMU",
        "Gaussian",
    }


def test_get_system():
    assert get_system("SI") is SI
    assert get_system("CGS-ESU") is CGS_ESU


def test_unknown_system():
    with pytest.raises(KeyError):
        get_system("UNKNOWN")


def test_si_units():
    assert SI.get_unit("meter").dimension == LENGTH
    assert SI.get_unit("kilogram").dimension == MASS
    assert SI.get_unit("newton").dimension == FORCE
    assert SI.get_unit("joule").dimension == ENERGY


def test_cgs_mechanical_scales():
    assert CGS_ESU.get_unit("centimeter").scale_to_si == pytest.approx(0.01)
    assert CGS_ESU.get_unit("gram").scale_to_si == pytest.approx(0.001)
    assert CGS_ESU.get_unit("dyne").scale_to_si == pytest.approx(1e-5)
    assert CGS_ESU.get_unit("erg").scale_to_si == pytest.approx(1e-7)


def test_esu_electrical_units():
    assert CGS_ESU.get_unit("statcoulomb").dimension == CHARGE
    assert CGS_ESU.get_unit("statvolt").dimension == VOLTAGE

    assert CGS_ESU.get_unit(
        "statcoulomb"
    ).scale_to_si == pytest.approx(3.3356409519815204e-10)

    assert CGS_ESU.get_unit(
        "statvolt"
    ).scale_to_si == pytest.approx(299.792458)


def test_emu_electrical_units():
    assert CGS_EMU.get_unit("abcoulomb").scale_to_si == 10
    assert CGS_EMU.get_unit("abampere").scale_to_si == 10
    assert CGS_EMU.get_unit("abvolt").scale_to_si == pytest.approx(1e-8)
    assert CGS_EMU.get_unit("abohm").scale_to_si == pytest.approx(1e-9)


def test_magnetic_units():
    assert CGS_EMU.get_unit("gauss").dimension == MAGNETIC_FIELD
    assert CGS_EMU.get_unit("gauss").scale_to_si == pytest.approx(1e-4)

    assert GAUSSIAN.get_unit("gauss").scale_to_si == pytest.approx(1e-4)


def test_unit_lookup_error():
    with pytest.raises(KeyError):
        SI.get_unit("unknown_unit")


def test_unit_mapping_is_immutable():
    with pytest.raises(TypeError):
        SI.units["new_unit"] = SI.get_unit("meter")

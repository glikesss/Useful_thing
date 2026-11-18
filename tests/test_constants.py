
import pytest

from units.constants import (
    C,
    E_CHARGE,
    H,
    HBAR,
    K_B,
    N_A,
    G,
    EPSILON_0,
    MU_0,
    M_ELECTRON,
    M_PROTON,
    M_NEUTRON,
    CONSTANTS,
    get_constant,
    ACTION,
    PERMITTIVITY,
    PERMEABILITY,
    GRAVITATIONAL_CONSTANT_DIM,
    BOLTZMANN_CONSTANT_DIM,
)

from units.dimensions import (
    LENGTH,
    TIME,
    MASS,
    CHARGE,
    AMOUNT,
    DIMENSIONLESS,
)


def test_speed_of_light():
    assert C.value == 299792458
    assert C.dimension == LENGTH / TIME


def test_elementary_charge():
    assert E_CHARGE.value == pytest.approx(1.602176634e-19)
    assert E_CHARGE.dimension == CHARGE


def test_planck_constants():
    assert H.dimension == ACTION
    assert HBAR.dimension == ACTION
    assert HBAR.value == pytest.approx(H.value / (2 * 3.141592653589793))


def test_boltzmann_constant():
    assert K_B.dimension == BOLTZMANN_CONSTANT_DIM
    assert K_B.value == pytest.approx(1.380649e-23)


def test_avogadro_constant():
    assert N_A.dimension == DIMENSIONLESS / AMOUNT
    assert N_A.value == pytest.approx(6.02214076e23)


def test_gravitational_constant():
    assert G.dimension == GRAVITATIONAL_CONSTANT_DIM
    assert G.value == pytest.approx(6.67430e-11)


def test_vacuum_constants():
    assert EPSILON_0.dimension == PERMITTIVITY
    assert MU_0.dimension == PERMEABILITY


def test_particle_masses():
    assert M_ELECTRON.dimension == MASS
    assert M_PROTON.dimension == MASS
    assert M_NEUTRON.dimension == MASS

    assert M_ELECTRON.value == pytest.approx(9.1093837139e-31)
    assert M_PROTON.value == pytest.approx(1.67262192595e-27)


def test_registry():
    assert get_constant("c") is C
    assert get_constant("h") is H
    assert get_constant("m_e") is M_ELECTRON


def test_unknown_constant():
    with pytest.raises(KeyError):
        get_constant("unknown")


def test_registry_is_immutable():
    with pytest.raises(TypeError):
        CONSTANTS["new"] = C

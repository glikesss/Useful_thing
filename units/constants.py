
from math import pi
from types import MappingProxyType

from .dimensions import (
    DIMENSIONLESS,
    LENGTH,
    MASS,
    TIME,
    TEMPERATURE,
    CURRENT,
    AMOUNT,
    ENERGY,
    CHARGE,
    FORCE,
)

from .quantities import Quantity


# ---------------------------------------------------------------------
# Derived dimensions
# ---------------------------------------------------------------------

ACTION = ENERGY * TIME
GRAVITATIONAL_CONSTANT_DIM = LENGTH ** 3 / (MASS * TIME ** 2)

PERMITTIVITY = CHARGE ** 2 / (FORCE * LENGTH ** 2)
PERMEABILITY = FORCE / (CURRENT ** 2)

BOLTZMANN_CONSTANT_DIM = ENERGY / TEMPERATURE


# ---------------------------------------------------------------------
# Fundamental constants (SI)
# ---------------------------------------------------------------------

# Speed of light in vacuum, m/s
C = Quantity(
    299792458,
    LENGTH / TIME,
)

# Elementary charge, C
E_CHARGE = Quantity(
    1.602176634e-19,
    CHARGE,
)

# Planck constant, J*s
H = Quantity(
    6.62607015e-34,
    ACTION,
)

# Reduced Planck constant, J*s
HBAR = Quantity(
    6.62607015e-34 / (2 * pi),
    ACTION,
)

# Boltzmann constant, J/K
K_B = Quantity(
    1.380649e-23,
    BOLTZMANN_CONSTANT_DIM,
)

# Avogadro constant, 1/mol
N_A = Quantity(
    6.02214076e23,
    DIMENSIONLESS / AMOUNT,
)

# Newtonian gravitational constant, m^3/(kg*s^2)
G = Quantity(
    6.67430e-11,
    GRAVITATIONAL_CONSTANT_DIM,
)

# Vacuum electric permittivity, F/m
EPSILON_0 = Quantity(
    8.8541878188e-12,
    PERMITTIVITY,
)

# Vacuum magnetic permeability, H/m
MU_0 = Quantity(
    1.25663706127e-6,
    PERMEABILITY,
)


# ---------------------------------------------------------------------
# Particle masses (kg)
# ---------------------------------------------------------------------

M_ELECTRON = Quantity(
    9.1093837139e-31,
    MASS,
)

M_PROTON = Quantity(
    1.67262192595e-27,
    MASS,
)

M_NEUTRON = Quantity(
    1.67492750056e-27,
    MASS,
)


# ---------------------------------------------------------------------
# Convenient aliases
# ---------------------------------------------------------------------

c = C
e = E_CHARGE
h = H
hbar = HBAR
k_B = K_B
N_A_value = N_A
epsilon_0 = EPSILON_0
mu_0 = MU_0


# ---------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------

CONSTANTS = MappingProxyType({
    "c": C,
    "e": E_CHARGE,
    "h": H,
    "hbar": HBAR,
    "k_B": K_B,
    "N_A": N_A,
    "G": G,
    "epsilon_0": EPSILON_0,
    "mu_0": MU_0,
    "m_e": M_ELECTRON,
    "m_p": M_PROTON,
    "m_n": M_NEUTRON,
})


def get_constant(name: str) -> Quantity:
    """Return a physical constant by its symbolic name."""
    try:
        return CONSTANTS[name]
    except KeyError:
        raise KeyError(
            f"Unknown physical constant: {name}"
        ) from None

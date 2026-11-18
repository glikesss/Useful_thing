
import math
from dataclasses import dataclass
from types import MappingProxyType

from .dimensions import (
    DIMENSIONLESS,
    LENGTH,
    MASS,
    TIME,
    CURRENT,
    TEMPERATURE,
    AMOUNT,
    LUMINOUS_INTENSITY,
    AREA,
    VOLUME,
    VELOCITY,
    ACCELERATION,
    FREQUENCY,
    FORCE,
    ENERGY,
    POWER,
    PRESSURE,
    DENSITY,
    CHARGE,
    VOLTAGE,
    RESISTANCE,
    CAPACITANCE,
    MAGNETIC_FIELD,
)


@dataclass(frozen=True)
class Unit:
    """
    Unit definition.

    scale_to_si:
        Multiplier converting this unit to the corresponding SI unit.

    Example:
        1 cm = 0.01 m
    """

    name: str
    symbol: str
    dimension: object
    scale_to_si: float
    system: str

    def __post_init__(self):
        if self.scale_to_si <= 0:
            raise ValueError("Unit scale must be positive")


@dataclass(frozen=True)
class UnitSystem:
    name: str
    symbol: str
    units: object

    def __post_init__(self):
        object.__setattr__(
            self,
            "units",
            MappingProxyType(dict(self.units)),
        )

    def get_unit(self, name: str) -> Unit:
        try:
            return self.units[name]
        except KeyError:
            raise KeyError(
                f"Unit {name!r} is not defined in {self.name}"
            ) from None


def _unit(name, symbol, dimension, scale, system):
    return Unit(
        name=name,
        symbol=symbol,
        dimension=dimension,
        scale_to_si=scale,
        system=system,
    )


# ---------------------------------------------------------------------
# SI
# ---------------------------------------------------------------------

SI_UNITS = {
    "dimensionless": _unit(
        "dimensionless", "1", DIMENSIONLESS, 1, "SI"
    ),
    "radian": _unit("radian", "rad", DIMENSIONLESS, 1, "SI"),
    "degree": _unit("degree", "deg", DIMENSIONLESS, math.pi / 180, "SI"),
    "meter": _unit("meter", "m", LENGTH, 1, "SI"),
    "kilogram": _unit("kilogram", "kg", MASS, 1, "SI"),
    "second": _unit("second", "s", TIME, 1, "SI"),
    "ampere": _unit("ampere", "A", CURRENT, 1, "SI"),
    "kelvin": _unit("kelvin", "K", TEMPERATURE, 1, "SI"),
    "mole": _unit("mole", "mol", AMOUNT, 1, "SI"),
    "candela": _unit("candela", "cd", LUMINOUS_INTENSITY, 1, "SI"),

    "hertz": _unit("hertz", "Hz", FREQUENCY, 1, "SI"),
    "newton": _unit("newton", "N", FORCE, 1, "SI"),
    "joule": _unit("joule", "J", ENERGY, 1, "SI"),
    "watt": _unit("watt", "W", POWER, 1, "SI"),
    "pascal": _unit("pascal", "Pa", PRESSURE, 1, "SI"),

    "coulomb": _unit("coulomb", "C", CHARGE, 1, "SI"),
    "volt": _unit("volt", "V", VOLTAGE, 1, "SI"),
    "ohm": _unit("ohm", "Ω", RESISTANCE, 1, "SI"),
    "farad": _unit("farad", "F", CAPACITANCE, 1, "SI"),
    "tesla": _unit("tesla", "T", MAGNETIC_FIELD, 1, "SI"),
}


# ---------------------------------------------------------------------
# CGS mechanical units
# ---------------------------------------------------------------------

CGS_MECHANICAL_UNITS = {
    "centimeter": _unit(
        "centimeter", "cm", LENGTH, 1e-2, "CGS"
    ),
    "gram": _unit(
        "gram", "g", MASS, 1e-3, "CGS"
    ),
    "second": _unit(
        "second", "s", TIME, 1, "CGS"
    ),
    "dyne": _unit(
        "dyne", "dyn", FORCE, 1e-5, "CGS"
    ),
    "erg": _unit(
        "erg", "erg", ENERGY, 1e-7, "CGS"
    ),
    "barye": _unit(
        "barye", "Ba", PRESSURE, 0.1, "CGS"
    ),
    "gal": _unit(
        "gal", "Gal", ACCELERATION, 1e-2, "CGS"
    ),
}


# ---------------------------------------------------------------------
# CGS-ESU: electrostatic system
# ---------------------------------------------------------------------

CGS_ESU_UNITS = {
    **CGS_MECHANICAL_UNITS,

    "statcoulomb": _unit(
        "statcoulomb", "statC", CHARGE,
        3.3356409519815204e-10, "CGS-ESU"
    ),
    "statampere": _unit(
        "statampere", "statA", CURRENT,
        3.3356409519815204e-10, "CGS-ESU"
    ),
    "statvolt": _unit(
        "statvolt", "statV", VOLTAGE,
        299.792458, "CGS-ESU"
    ),
    "statohm": _unit(
        "statohm", "statΩ", RESISTANCE,
        8.987551787368176e11, "CGS-ESU"
    ),
}


# ---------------------------------------------------------------------
# CGS-EMU: electromagnetic system
# ---------------------------------------------------------------------

CGS_EMU_UNITS = {
    **CGS_MECHANICAL_UNITS,

    "abcoulomb": _unit(
        "abcoulomb", "abC", CHARGE, 10, "CGS-EMU"
    ),
    "abampere": _unit(
        "abampere", "abA", CURRENT, 10, "CGS-EMU"
    ),
    "abvolt": _unit(
        "abvolt", "abV", VOLTAGE, 1e-8, "CGS-EMU"
    ),
    "abohm": _unit(
        "abohm", "abΩ", RESISTANCE, 1e-9, "CGS-EMU"
    ),
    "maxwell": _unit(
        "maxwell", "Mx", MAGNETIC_FIELD * AREA,
        1e-8, "CGS-EMU"
    ),
    "gauss": _unit(
        "gauss", "G", MAGNETIC_FIELD, 1e-4, "CGS-EMU"
    ),
}


# ---------------------------------------------------------------------
# Gaussian system
# ---------------------------------------------------------------------

GAUSSIAN_UNITS = {
    **CGS_MECHANICAL_UNITS,

    "statcoulomb": _unit(
        "statcoulomb", "statC", CHARGE,
        3.3356409519815204e-10, "Gaussian"
    ),
    "statampere": _unit(
        "statampere", "statA", CURRENT,
        3.3356409519815204e-10, "Gaussian"
    ),
    "statvolt": _unit(
        "statvolt", "statV", VOLTAGE,
        299.792458, "Gaussian"
    ),
    "gauss": _unit(
        "gauss", "G", MAGNETIC_FIELD, 1e-4, "Gaussian"
    ),
    "maxwell": _unit(
        "maxwell", "Mx", MAGNETIC_FIELD * AREA,
        1e-8, "Gaussian"
    ),
}


SI = UnitSystem("International System of Units", "SI", SI_UNITS)

CGS_ESU = UnitSystem(
    "Centimeter-Gram-Second Electrostatic System",
    "CGS-ESU",
    CGS_ESU_UNITS,
)

CGS_EMU = UnitSystem(
    "Centimeter-Gram-Second Electromagnetic System",
    "CGS-EMU",
    CGS_EMU_UNITS,
)

GAUSSIAN = UnitSystem(
    "Gaussian CGS System",
    "Gaussian",
    GAUSSIAN_UNITS,
)

SYSTEMS = {
    "SI": SI,
    "CGS-ESU": CGS_ESU,
    "CGS-EMU": CGS_EMU,
    "Gaussian": GAUSSIAN,
}


def get_system(name: str) -> UnitSystem:
    try:
        return SYSTEMS[name]
    except KeyError:
        raise KeyError(f"Unknown unit system: {name}") from None

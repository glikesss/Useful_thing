
from types import MappingProxyType

from .systems import SI, CGS_ESU, CGS_EMU, GAUSSIAN


_UNIT_ALIASES = {
    # SI base units
    "m": (SI, "meter"),
    "meter": (SI, "meter"),
    "kg": (SI, "kilogram"),
    "kilogram": (SI, "kilogram"),
    "s": (SI, "second"),
    "second": (SI, "second"),
    "A": (SI, "ampere"),
    "ampere": (SI, "ampere"),
    "K": (SI, "kelvin"),
    "kelvin": (SI, "kelvin"),
    "mol": (SI, "mole"),
    "mole": (SI, "mole"),
    "cd": (SI, "candela"),
    "candela": (SI, "candela"),

    # SI derived units
    "rad": (SI, "radian"),
    "radian": (SI, "radian"),
    "deg": (SI, "degree"),
    "degree": (SI, "degree"),
    "Hz": (SI, "hertz"),
    "hertz": (SI, "hertz"),
    "N": (SI, "newton"),
    "newton": (SI, "newton"),
    "J": (SI, "joule"),
    "joule": (SI, "joule"),
    "W": (SI, "watt"),
    "watt": (SI, "watt"),
    "Pa": (SI, "pascal"),
    "pascal": (SI, "pascal"),
    "C": (SI, "coulomb"),
    "coulomb": (SI, "coulomb"),
    "V": (SI, "volt"),
    "volt": (SI, "volt"),
    "ohm": (SI, "ohm"),
    "F": (SI, "farad"),
    "farad": (SI, "farad"),
    "T": (SI, "tesla"),
    "tesla": (SI, "tesla"),

    # CGS mechanical
    "cm": (CGS_ESU, "centimeter"),
    "centimeter": (CGS_ESU, "centimeter"),
    "g": (CGS_ESU, "gram"),
    "gram": (CGS_ESU, "gram"),
    "dyn": (CGS_ESU, "dyne"),
    "dyne": (CGS_ESU, "dyne"),
    "erg": (CGS_ESU, "erg"),
    "Ba": (CGS_ESU, "barye"),
    "barye": (CGS_ESU, "barye"),
    "Gal": (CGS_ESU, "gal"),
    "gal": (CGS_ESU, "gal"),

    # CGS-ESU
    "statC": (CGS_ESU, "statcoulomb"),
    "statcoulomb": (CGS_ESU, "statcoulomb"),
    "statA": (CGS_ESU, "statampere"),
    "statampere": (CGS_ESU, "statampere"),
    "statV": (CGS_ESU, "statvolt"),
    "statvolt": (CGS_ESU, "statvolt"),
    "statohm": (CGS_ESU, "statohm"),

    # CGS-EMU
    "abC": (CGS_EMU, "abcoulomb"),
    "abcoulomb": (CGS_EMU, "abcoulomb"),
    "abA": (CGS_EMU, "abampere"),
    "abampere": (CGS_EMU, "abampere"),
    "abV": (CGS_EMU, "abvolt"),
    "abvolt": (CGS_EMU, "abvolt"),
    "abohm": (CGS_EMU, "abohm"),

    # Magnetic units
    "gauss": (GAUSSIAN, "gauss"),
    "maxwell": (GAUSSIAN, "maxwell"),
    "Mx": (GAUSSIAN, "maxwell"),
}


def _build_registry():
    registry = {}

    for alias, (system, unit_name) in _UNIT_ALIASES.items():
        registry[alias] = system.get_unit(unit_name)

    return MappingProxyType(registry)


UNITS = _build_registry()


def get_unit(name: str):
    try:
        return UNITS[name]
    except KeyError:
        raise KeyError(f"Unknown unit: {name}") from None


def is_unit(name: str) -> bool:
    return name in UNITS

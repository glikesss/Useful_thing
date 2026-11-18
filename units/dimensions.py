
from dataclasses import dataclass
from fractions import Fraction
from collections.abc import Mapping


BASE_DIMENSIONS = (
    "L",  # Length
    "M",  # Mass
    "T",  # Time
    "I",  # Electric current
    "Θ",  # Thermodynamic temperature
    "N",  # Amount of substance
    "J",  # Luminous intensity
)

DIMENSION_COUNT = len(BASE_DIMENSIONS)


@dataclass(frozen=True)
class Dimension:
    """
    Physical dimension represented by seven rational exponents.

    Exponent order:
        L, M, T, I, Θ, N, J
    """

    exponents: tuple[Fraction, ...] = (
        Fraction(0),
        Fraction(0),
        Fraction(0),
        Fraction(0),
        Fraction(0),
        Fraction(0),
        Fraction(0),
    )

    def __post_init__(self):
        if len(self.exponents) != DIMENSION_COUNT:
            raise ValueError(
                f"Expected {DIMENSION_COUNT} exponents"
            )

        normalized = tuple(
            Fraction(value)
            for value in self.exponents
        )

        object.__setattr__(self, "exponents", normalized)

    @classmethod
    def base(cls, name: str):
        """Create one of the seven base dimensions."""
        try:
            index = BASE_DIMENSIONS.index(name)
        except ValueError:
            raise ValueError(
                f"Unknown base dimension: {name}"
            ) from None

        values = [Fraction(0)] * DIMENSION_COUNT
        values[index] = Fraction(1)

        return cls(tuple(values))

    @classmethod
    def from_mapping(cls, values: Mapping[str, int | float | Fraction]):
        """Create a dimension from a mapping such as {'L': 1, 'T': -2}."""
        exponents = [Fraction(0)] * DIMENSION_COUNT

        for name, power in values.items():
            try:
                index = BASE_DIMENSIONS.index(name)
            except ValueError:
                raise ValueError(
                    f"Unknown base dimension: {name}"
                ) from None

            exponents[index] = Fraction(power)

        return cls(tuple(exponents))

    @property
    def is_dimensionless(self) -> bool:
        return all(power == 0 for power in self.exponents)

    def __mul__(self, other):
        if not isinstance(other, Dimension):
            return NotImplemented

        return Dimension(tuple(
            a + b
            for a, b in zip(self.exponents, other.exponents)
        ))

    def __truediv__(self, other):
        if not isinstance(other, Dimension):
            return NotImplemented

        return Dimension(tuple(
            a - b
            for a, b in zip(self.exponents, other.exponents)
        ))

    def __pow__(self, power):
        power = Fraction(power)

        return Dimension(tuple(
            exponent * power
            for exponent in self.exponents
        ))

    def __str__(self):
        if self.is_dimensionless:
            return "1"

        parts = []

        for name, power in zip(BASE_DIMENSIONS, self.exponents):
            if power == 0:
                continue

            if power == 1:
                parts.append(name)
            else:
                parts.append(f"{name}^{power}")

        return " ".join(parts)

    def __repr__(self):
        return f"Dimension('{self}')"


# Base dimensions

DIMENSIONLESS = Dimension()

LENGTH = Dimension.base("L")
MASS = Dimension.base("M")
TIME = Dimension.base("T")
CURRENT = Dimension.base("I")
TEMPERATURE = Dimension.base("Θ")
AMOUNT = Dimension.base("N")
LUMINOUS_INTENSITY = Dimension.base("J")


# Derived dimensions

AREA = LENGTH ** 2
VOLUME = LENGTH ** 3

VELOCITY = LENGTH / TIME
ACCELERATION = LENGTH / TIME ** 2

FREQUENCY = DIMENSIONLESS / TIME

FORCE = MASS * ACCELERATION
ENERGY = FORCE * LENGTH
POWER = ENERGY / TIME

PRESSURE = FORCE / AREA
DENSITY = MASS / VOLUME

CHARGE = CURRENT * TIME
VOLTAGE = ENERGY / CHARGE
RESISTANCE = VOLTAGE / CURRENT
CAPACITANCE = CHARGE / VOLTAGE

MAGNETIC_FIELD = MASS / (CURRENT * TIME ** 2)

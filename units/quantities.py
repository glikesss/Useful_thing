
from dataclasses import dataclass
from numbers import Number

import numpy as np

from .dimensions import DIMENSIONLESS, Dimension
from core.errors import DimensionError

import sympy as sp

from dataclasses import dataclass, field
from collections.abc import Mapping
from types import MappingProxyType

import sympy as sp


@dataclass(frozen=True, eq=False)
class Quantity:
    value: object
    dimension: Dimension = DIMENSIONLESS

    __array_priority__ = 1000

    def __post_init__(self):
        if not isinstance(self.dimension, Dimension):
            raise TypeError("dimension must be a Dimension")

    def _check_compatible(self, other):
        if not isinstance(other, Quantity):
            raise DimensionError(
                "Операция требует физическую величину"
            )

        if self.dimension != other.dimension:
            raise DimensionError(
                f"Несовместимые размерности: "
                f"{self.dimension} и {other.dimension}"
            )

    def __add__(self, other):
        self._check_compatible(other)

        return Quantity(
            self.value + other.value,
            self.dimension,
        )

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        self._check_compatible(other)

        return Quantity(
            self.value - other.value,
            self.dimension,
        )

    def __rsub__(self, other):
        if not isinstance(other, Quantity):
            return NotImplemented

        return other.__sub__(self)

    def __mul__(self, other):
        if isinstance(other, Quantity):
            return Quantity(
                self.value * other.value,
                self.dimension * other.dimension,
            )

        if isinstance(other, Number) or isinstance(other, np.ndarray):
            return Quantity(
                self.value * other,
                self.dimension,
            )

        return NotImplemented

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, Quantity):
            return Quantity(
                self.value / other.value,
                self.dimension / other.dimension,
            )

        if isinstance(other, Number) or isinstance(other, np.ndarray):
            return Quantity(
                self.value / other,
                self.dimension,
            )

        return NotImplemented

    def __rtruediv__(self, other):
        if isinstance(other, Number) or isinstance(other, np.ndarray):
            return Quantity(
                other / self.value,
                DIMENSIONLESS / self.dimension,
            )

        return NotImplemented

    def __pow__(self, power):
        if isinstance(power, Quantity):
            if not power.dimension.is_dimensionless:
                raise DimensionError(
                    "Показатель степени должен быть безразмерным"
                )
            power = power.value

        if not isinstance(power, Number):
            raise TypeError(
                "Показатель степени должен быть числом"
            )

        return Quantity(
            self.value ** power,
            self.dimension ** power,
        )

    def __neg__(self):
        return Quantity(
            -self.value,
            self.dimension,
        )

    def __pos__(self):
        return self

    def __abs__(self):
        return Quantity(
            abs(self.value),
            self.dimension,
        )

    def __eq__(self, other):
        if not isinstance(other, Quantity):
            return False

        if self.dimension != other.dimension:
            return False

        return bool(np.array_equal(self.value, other.value))

    def __lt__(self, other):
        self._check_compatible(other)
        return self.value < other.value

    def __le__(self, other):
        self._check_compatible(other)
        return self.value <= other.value

    def __gt__(self, other):
        self._check_compatible(other)
        return self.value > other.value

    def __ge__(self, other):
        self._check_compatible(other)
        return self.value >= other.value

    @property
    def is_dimensionless(self):
        return self.dimension.is_dimensionless

    def __repr__(self):
        return (
            f"Quantity(value={self.value!r}, "
            f"dimension={self.dimension!r})"
        )

    def __str__(self):
        return f"{self.value} [{self.dimension}]"


    
@dataclass(frozen=True, eq=False)
class SymbolicQuantity:
    expression: sp.Expr
    dimension: Dimension | None = None
    symbol_dimensions: Mapping = field(default_factory=dict)

    def __post_init__(self):
        expression = sp.sympify(self.expression)

        if self.dimension is not None and not isinstance(
            self.dimension, Dimension
        ):
            raise TypeError("dimension must be a Dimension")

        dimensions = {}

        for symbol, dimension in self.symbol_dimensions.items():
            symbol = sp.sympify(symbol)

            if not isinstance(symbol, sp.Symbol):
                raise TypeError("Dimension keys must be SymPy symbols")

            if not isinstance(dimension, Dimension):
                raise TypeError("Symbol dimensions must be Dimension")

            dimensions[symbol] = dimension

        object.__setattr__(self, "expression", expression)
        object.__setattr__(
            self,
            "symbol_dimensions",
            MappingProxyType(dimensions),
        )

        if dimensions:
            inferred = self._infer_dimension(expression, dimensions)

            if self.dimension is None:
                object.__setattr__(self, "dimension", inferred)

        elif self.dimension is None:
            if expression.free_symbols:
                raise DimensionError(
                    "Symbol dimensions are required for symbolic expressions"
                )

            object.__setattr__(self, "dimension", DIMENSIONLESS)

    @classmethod
    def _infer_dimension(cls, expression, dimensions):
        expression = sp.sympify(expression)

        if expression.is_Number or expression.is_NumberSymbol:
            return DIMENSIONLESS

        if expression.is_Symbol:
            try:
                return dimensions[expression]
            except KeyError:
                raise DimensionError(
                    f"Unknown symbol dimension: {expression}"
                ) from None

        if expression.is_Add:
            result = cls._infer_dimension(
                expression.args[0], dimensions
            )

            for term in expression.args[1:]:
                current = cls._infer_dimension(term, dimensions)

                if current != result:
                    raise DimensionError(
                        "Cannot add expressions with different dimensions: "
                        f"{result} and {current}"
                    )

            return result

        if expression.is_Mul:
            result = DIMENSIONLESS

            for factor in expression.args:
                result = result * cls._infer_dimension(
                    factor, dimensions
                )

            return result

        if expression.is_Pow:
            base, exponent = expression.args
            base_dimension = cls._infer_dimension(base, dimensions)
            exponent_dimension = cls._infer_dimension(
                exponent, dimensions
            )

            if not exponent_dimension.is_dimensionless:
                raise DimensionError(
                    "Exponent must be dimensionless"
                )

            if not exponent.is_number:
                if not base_dimension.is_dimensionless:
                    raise DimensionError(
                        "Dimensioned base requires a numeric exponent"
                    )

                return DIMENSIONLESS

            return base_dimension ** exponent

        if expression.is_Function:
            name = expression.func.__name__

            if name in ("Abs",):
                return cls._infer_dimension(
                    expression.args[0], dimensions
                )

            for argument in expression.args:
                argument_dimension = cls._infer_dimension(
                    argument, dimensions
                )

                if not argument_dimension.is_dimensionless:
                    raise DimensionError(
                        f"Function {name} requires dimensionless arguments"
                    )

            return DIMENSIONLESS

        raise DimensionError(
            f"Cannot determine dimension of expression: {expression}"
        )

    @staticmethod
    def _merge_dimensions(first, second):
        result = dict(first)

        for symbol, dimension in second.items():
            if symbol in result and result[symbol] != dimension:
                raise DimensionError(
                    f"Conflicting dimensions for symbol {symbol}"
                )

            result[symbol] = dimension

        return result

    @staticmethod
    def _coerce_additive_scalar(value):
        try:
            expression = sp.sympify(value)
        except (TypeError, ValueError, sp.SympifyError):
            raise DimensionError(
                "Addition and subtraction require compatible dimensions"
            ) from None

        if not expression.is_number:
            raise DimensionError(
                "Only numeric scalars can be added to SymbolicQuantity"
            )

        return SymbolicQuantity(expression, DIMENSIONLESS)

    def _check_compatible(self, other):
        if not isinstance(other, SymbolicQuantity):
            raise DimensionError(
                "Operation requires another SymbolicQuantity"
            )

        if self.dimension != other.dimension:
            raise DimensionError(
                f"Incompatible dimensions: "
                f"{self.dimension} and {other.dimension}"
            )

    def __add__(self, other):
        if not isinstance(other, SymbolicQuantity):
            other = self._coerce_additive_scalar(other)

        self._check_compatible(other)

        dimensions = self._merge_dimensions(
            self.symbol_dimensions,
            other.symbol_dimensions,
        )

        return SymbolicQuantity(
            self.expression + other.expression,
            self.dimension,
            dimensions,
        )

    def __radd__(self, other):
        return self.__add__(other)

    def __sub__(self, other):
        if not isinstance(other, SymbolicQuantity):
            other = self._coerce_additive_scalar(other)

        self._check_compatible(other)

        dimensions = self._merge_dimensions(
            self.symbol_dimensions,
            other.symbol_dimensions,
        )

        return SymbolicQuantity(
            self.expression - other.expression,
            self.dimension,
            dimensions,
        )

    def __rsub__(self, other):
        if not isinstance(other, SymbolicQuantity):
            other = self._coerce_additive_scalar(other)

        return other.__sub__(self)

    def __mul__(self, other):
        if isinstance(other, Quantity):
            return SymbolicQuantity(
                self.expression * sp.sympify(other.value),
                self.dimension * other.dimension,
                self.symbol_dimensions,
            )

        if isinstance(other, SymbolicQuantity):
            dimensions = self._merge_dimensions(
                self.symbol_dimensions,
                other.symbol_dimensions,
            )

            return SymbolicQuantity(
                self.expression * other.expression,
                self.dimension * other.dimension,
                dimensions,
            )

        return SymbolicQuantity(
            self.expression * sp.sympify(other),
            self.dimension,
            self.symbol_dimensions,
        )

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, Quantity):
            return SymbolicQuantity(
                self.expression / sp.sympify(other.value),
                self.dimension / other.dimension,
                self.symbol_dimensions,
            )

        if isinstance(other, SymbolicQuantity):
            dimensions = self._merge_dimensions(
                self.symbol_dimensions,
                other.symbol_dimensions,
            )

            return SymbolicQuantity(
                self.expression / other.expression,
                self.dimension / other.dimension,
                dimensions,
            )

        return SymbolicQuantity(
            self.expression / sp.sympify(other),
            self.dimension,
            self.symbol_dimensions,
        )

    def __rtruediv__(self, other):
        if isinstance(other, Quantity):
            return SymbolicQuantity(
                sp.sympify(other.value) / self.expression,
                other.dimension / self.dimension,
                self.symbol_dimensions,
            )

        return SymbolicQuantity(
            sp.sympify(other) / self.expression,
            DIMENSIONLESS / self.dimension,
            self.symbol_dimensions,
        )

    def __pow__(self, power):
        if isinstance(power, SymbolicQuantity):
            if not power.dimension.is_dimensionless:
                raise DimensionError("Exponent must be dimensionless")

            power = power.expression

        power = sp.sympify(power)

        if not power.is_number and not self.dimension.is_dimensionless:
            raise DimensionError(
                "A dimensioned quantity requires a numeric exponent"
            )

        return SymbolicQuantity(
            self.expression ** power,
            self.dimension ** power if power.is_number else DIMENSIONLESS,
            self.symbol_dimensions,
        )

    def __neg__(self):
        return SymbolicQuantity(
            -self.expression,
            self.dimension,
            self.symbol_dimensions,
        )

    def __pos__(self):
        return self

    def __abs__(self):
        return SymbolicQuantity(
            sp.Abs(self.expression),
            self.dimension,
            self.symbol_dimensions,
        )

    def diff(self, variable, order=1):
        if not isinstance(variable, sp.Symbol):
            raise TypeError("variable must be a SymPy Symbol")

        if not isinstance(order, int) or order < 0:
            raise ValueError(
                "Differentiation order must be non-negative"
            )

        variable_dimension = self.symbol_dimensions.get(variable)

        result_dimension = self.dimension

        if variable_dimension is not None:
            result_dimension = (
                result_dimension / (variable_dimension ** order)
            )

        return SymbolicQuantity(
            sp.diff(self.expression, variable, order),
            result_dimension,
            self.symbol_dimensions,
        )

    def integrate(
        self,
        variable,
        lower=None,
        upper=None,
        variable_dimension=None,
    ):
        if not isinstance(variable, sp.Symbol):
            raise TypeError("variable must be a SymPy Symbol")

        if (lower is None) != (upper is None):
            raise ValueError("Both integration limits must be specified")

        if variable_dimension is None:
            variable_dimension = self.symbol_dimensions.get(variable)

        if variable_dimension is None:
            raise ValueError(
                "variable_dimension must be specified"
            )

        if not isinstance(variable_dimension, Dimension):
            raise TypeError(
                "variable_dimension must be a Dimension"
            )

        if lower is None:
            result = sp.integrate(self.expression, variable)
        else:
            if isinstance(lower, Quantity):
                if lower.dimension != variable_dimension:
                    raise DimensionError(
                        "Lower integration limit has incompatible dimension"
                    )
                lower = lower.value

            elif isinstance(lower, SymbolicQuantity):
                if lower.dimension != variable_dimension:
                    raise DimensionError(
                        "Lower integration limit has incompatible dimension"
                    )
                lower = lower.expression

            if isinstance(upper, Quantity):
                if upper.dimension != variable_dimension:
                    raise DimensionError(
                        "Upper integration limit has incompatible dimension"
                    )
                upper = upper.value

            elif isinstance(upper, SymbolicQuantity):
                if upper.dimension != variable_dimension:
                    raise DimensionError(
                        "Upper integration limit has incompatible dimension"
                    )
                upper = upper.expression

            result = sp.integrate(
                self.expression,
                (variable, sp.sympify(lower), sp.sympify(upper)),
            )

        return SymbolicQuantity(
            result,
            self.dimension * variable_dimension,
            self.symbol_dimensions,
        )

    def subs(self, *args, **kwargs):
        return SymbolicQuantity(
            self.expression.subs(*args, **kwargs),
            self.dimension,
            self.symbol_dimensions,
        )

    def simplify(self):
        return SymbolicQuantity(
            sp.simplify(self.expression),
            self.dimension,
            self.symbol_dimensions,
        )

    def __eq__(self, other):
        if not isinstance(other, SymbolicQuantity):
            return False

        return (
            self.dimension == other.dimension
            and sp.simplify(
                self.expression - other.expression
            ) == 0
        )

    def __repr__(self):
        return (
            f"SymbolicQuantity("
            f"expression={self.expression!r}, "
            f"dimension={self.dimension!r}, "
            f"symbol_dimensions={dict(self.symbol_dimensions)!r})"
        )

    def __str__(self):
        return f"{self.expression} [{self.dimension}]"
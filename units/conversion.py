
from numbers import Number

import numpy as np

from core.errors import DimensionError
from .quantities import Quantity
from .systems import Unit


def _validate_units(source: Unit, target: Unit):
    if not isinstance(source, Unit) or not isinstance(target, Unit):
        raise TypeError("source и target должны быть объектами Unit")

    if source.dimension != target.dimension:
        raise DimensionError(
            f"Нельзя перевести {source.symbol} "
            f"({source.dimension}) в {target.symbol} "
            f"({target.dimension})"
        )


def convert_value(value, source: Unit, target: Unit):
    """
    Convert a numerical value from one unit to another.

    Example:
        convert_value(100, cm, m) == 1
    """
    _validate_units(source, target)

    if not isinstance(value, (Number, np.ndarray, list, tuple)):
        raise TypeError("Значение должно быть числом или массивом")

    return np.asarray(value) * (
        source.scale_to_si / target.scale_to_si
    ) if isinstance(value, (np.ndarray, list, tuple)) else (
        value * source.scale_to_si / target.scale_to_si
    )


def convert_quantity(
    quantity: Quantity,
    source: Unit,
    target: Unit,
) -> Quantity:
    """
    Convert a Quantity from source unit to target unit.

    quantity.value is interpreted in source units.
    The returned Quantity.value is expressed in target units.
    """
    if not isinstance(quantity, Quantity):
        raise TypeError("quantity должен быть объектом Quantity")

    _validate_units(source, target)

    if quantity.dimension != source.dimension:
        raise DimensionError(
            f"Размерность величины {quantity.dimension} "
            f"не соответствует единице {source.symbol} "
            f"({source.dimension})"
        )

    converted_value = convert_value(
        quantity.value,
        source,
        target,
    )

    return Quantity(
        value=converted_value,
        dimension=target.dimension,
    )

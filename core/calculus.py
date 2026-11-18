import numpy as np
import sympy as sp

from scipy.integrate import quad, cumulative_trapezoid

from .errors import EvaluationError, ParseError


def _validate_variable(variable):
    if not isinstance(variable, sp.Symbol):
        raise ParseError(
            "В качестве переменной дифференцирования или интегрирования "
            "нужно указать имя, например x"
        )


def differentiate(expression, variable, order=1):
    _validate_variable(variable)

    if not isinstance(order, (int, sp.Integer)) or order < 1:
        raise ParseError("Порядок производной должен быть положительным целым числом")

    return sp.diff(expression, variable, int(order))


def integrate(expression, variable, lower=None, upper=None):
    _validate_variable(variable)

    if lower is None and upper is None:
        return sp.integrate(expression, variable)

    if lower is None or upper is None:
        raise ParseError("Нужно указать оба предела интегрирования")

    return sp.integrate(
        expression,
        (variable, lower, upper),
    )


def cumulative_integral(expression, variable, start):
    """
    Символьный накопительный интеграл:
        F(x) = integral(expression, x, start, x)
    """

    _validate_variable(variable)

    dummy = sp.Dummy("integration_variable")

    integrand = expression.subs(variable, dummy)

    return sp.integrate(
        integrand,
        (dummy, start, variable),
    )


def numerical_integral(expression, variable, lower, upper, parameters=None):
    """
    Численное вычисление определённого интеграла.
    """

    _validate_variable(variable)

    parameters = parameters or {}

    expression = expression.subs({
        sp.Symbol(name): value
        for name, value in parameters.items()
    })

    if expression.free_symbols - {variable}:
        raise EvaluationError(
            "В интеграле остались неопределённые переменные: "
            + ", ".join(map(str, expression.free_symbols - {variable}))
        )

    function = sp.lambdify(
        variable,
        expression,
        modules=["numpy", "math"],
    )

    try:
        result, error = quad(
            lambda value: float(function(value)),
            float(lower),
            float(upper),
        )

        return result

    except Exception as exc:
        raise EvaluationError(
            f"Ошибка численного интегрирования: {exc}"
        ) from exc


def numerical_cumulative_integral(
    expression,
    variable,
    start,
    values,
    parameters=None,
):
    """
    Численный накопительный интеграл для массива значений.

    Возвращает массив:
        F(x_i) = integral from start to x_i of f(x) dx

    Метод: составная формула трапеций.
    """

    _validate_variable(variable)

    values = np.asarray(values, dtype=float)

    if values.ndim != 1:
        raise EvaluationError(
            "Накопительный интеграл принимает одномерный массив"
        )

    if values.size == 0:
        return np.array([], dtype=float)

    if not np.all(np.isfinite(values)):
        raise EvaluationError(
            "Массив содержит NaN или бесконечные значения"
        )

    parameters = parameters or {}

    expression = expression.subs({
        sp.Symbol(name): value
        for name, value in parameters.items()
    })

    unresolved = expression.free_symbols - {variable}

    if unresolved:
        raise EvaluationError(
            "Неизвестные переменные: "
            + ", ".join(map(str, unresolved))
        )

    function = sp.lambdify(
        variable,
        expression,
        modules=["numpy", "math"],
    )

    grid = np.concatenate(([float(start)], values))

    differences = np.diff(grid)

    if not (
        np.all(differences >= 0)
        or np.all(differences <= 0)
    ):
        raise EvaluationError(
            "Значения x должны идти в монотонном порядке"
        )

    try:
        result_values = np.asarray(function(grid), dtype=float)

        if result_values.ndim == 0:
            result_values = np.full_like(grid, result_values)

        if not np.all(np.isfinite(result_values)):
            raise EvaluationError(
                "Функция вернула NaN или бесконечность"
            )

        result = cumulative_trapezoid(
            result_values,
            x=grid,
            initial=0.0,
        )

        return result[1:]

    except EvaluationError:
        raise
    except Exception as exc:
        raise EvaluationError(
            f"Ошибка накопительного интегрирования: {exc}"
        ) from exc
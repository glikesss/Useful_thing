import math

import pytest

from core import MathEngine
from units.dimensions import LENGTH


def make_engine():
    engine = MathEngine()
    engine.lines = [
        "identity(x) = x",
        "inverse(x) = 1/x",
        "square(x) = x**2",
        "root(x) = sqrt(x)",
        "logarithm(x) = log(x)",
        "exponential(x) = exp(x)",
        "arcsine(x) = asin(x)",
    ]
    engine._rebuild()
    return engine


@pytest.mark.parametrize("value", [0, 0.0])
def test_division_by_zero(value):
    engine = make_engine()
    with pytest.raises(Exception):
        engine.call("inverse", value)


def test_sqrt_negative_argument():
    engine = make_engine()
    with pytest.raises(Exception):
        engine.call("root", -1)


def test_log_zero_argument():
    engine = make_engine()
    with pytest.raises(Exception):
        engine.call("logarithm", 0)


def test_log_negative_argument():
    engine = make_engine()
    with pytest.raises(Exception):
        engine.call("logarithm", -1)


@pytest.mark.parametrize("value", [-2, 2])
def test_arcsine_outside_domain(value):
    engine = make_engine()
    with pytest.raises(Exception):
        engine.call("arcsine", value)


def test_exponential_overflow():
    engine = make_engine()
    with pytest.raises(Exception):
        engine.call("exponential", 10000)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_non_finite_input_is_rejected(value):
    engine = make_engine()
    with pytest.raises(Exception):
        engine.call("identity", value)


def test_non_finite_result_is_rejected():
    engine = make_engine()
    with pytest.raises(Exception):
        engine.call("square", float("inf"))


def test_engine_recovers_after_numeric_error():
    engine = make_engine()

    with pytest.raises(Exception):
        engine.call("inverse", 0)

    assert engine.call("square", 3) == 9
    assert engine.call("identity", 5) == 5


def test_symbolic_expression_survives_numeric_errors():
    engine = make_engine()
    engine.set_symbolic_variable("z", "z", LENGTH)

    with pytest.raises(Exception):
        engine.call("inverse", 0)

    result = engine.call("square", engine.variables.get("z"))
    assert result.dimension == LENGTH**2


def test_repeated_numeric_errors_do_not_corrupt_engine():
    engine = make_engine()

    for _ in range(3):
        with pytest.raises(Exception):
            engine.call("inverse", 0)

    assert engine.call("square", 4) == 16

import numpy as np
import pytest

from core.engine import MathEngine


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("[1,...,10]", np.arange(1, 11, dtype=float)),
        ("[1, …, 10]", np.arange(1, 11, dtype=float)),
        ("[1, ⋯, 10]", np.arange(1, 11, dtype=float)),
        (r"[1,\\ldots,10]", np.arange(1, 11, dtype=float)),
        ("[1,1.1,...,2]", np.arange(1.1, 2.01, 0.1)),
    ],
)
def test_ellipsis_sequence_notation(expression, expected):
    engine = MathEngine()
    assert np.allclose(engine.evaluate(expression), expected)


def test_ellipsis_sequence_in_variable_definition():
    engine = MathEngine()
    engine.set_lines(["a=[1, …, 10]"])
    assert np.array_equal(engine.get_variable("a"), np.arange(1, 11, dtype=float))

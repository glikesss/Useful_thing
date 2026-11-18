import pytest

from core import MathEngine
from core.errors import EvaluationError, ParseError


def test_duplicate_function_definition():
    engine = MathEngine()
    engine.lines = ["f(x) = x", "f(y) = y"]
    with pytest.raises(EvaluationError):
        engine._rebuild()


@pytest.mark.parametrize("lines", [
    ["f(x) = x", "f = 2"],
    ["f = 2", "f(x) = x"],
])
def test_variable_function_name_collision(lines):
    engine = MathEngine()
    engine.lines = lines
    with pytest.raises(EvaluationError):
        engine._rebuild()


@pytest.mark.parametrize("source", [
    "f(x, x) = x",
    "f(x, x=2) = x",
    "f(x+1) = x",
    "f() = 1",
    "f(x) = x +",
    "f(x, **kwargs) = x",
])
def test_invalid_function_definitions(source):
    engine = MathEngine()
    engine.lines = [source]
    with pytest.raises((ParseError, EvaluationError)):
        engine._rebuild()


def test_default_argument_and_keyword_call():
    engine = MathEngine()
    engine.lines = ["f(x, y=2) = x + y"]
    engine._rebuild()

    assert engine.evaluate("f(3)") == 5
    assert engine.evaluate("f(y=4, x=3)") == 7


@pytest.mark.parametrize("source", [
    "f(1, x=2)",
    "f(1, unknown=2)",
    "f(1, 2, 3)",
])
def test_invalid_user_function_calls(source):
    engine = MathEngine()
    engine.lines = ["f(x, y=2) = x + y", f"result = {source}"]
    with pytest.raises((ParseError, EvaluationError)):
        engine._rebuild()


def test_add_line_rolls_back_after_error():
    engine = MathEngine()
    engine.add_line("a = 2")

    with pytest.raises(Exception):
        engine.add_line("broken = ")

    assert engine.lines == ["a = 2"]
    assert engine.evaluate("a") == 2


def test_update_line_rolls_back_after_error():
    engine = MathEngine()
    engine.add_line("a = 2")

    with pytest.raises(Exception):
        engine.update_line(0, "a = ")

    assert engine.lines == ["a = 2"]
    assert engine.evaluate("a") == 2


def test_remove_line_rolls_back_after_error():
    engine = MathEngine()
    engine.set_lines(["a = 2", "b = a + 3"])

    with pytest.raises(Exception):
        engine.remove_line(0)

    assert engine.lines == ["a = 2", "b = a + 3"]
    assert engine.evaluate("b") == 5


def test_set_lines_rolls_back_after_error():
    engine = MathEngine()
    engine.set_lines(["a = 2"])

    with pytest.raises(Exception):
        engine.set_lines(["broken = "])

    assert engine.lines == ["a = 2"]
    assert engine.evaluate("a") == 2

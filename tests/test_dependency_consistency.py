import pytest

from core import MathEngine


def test_forward_variable_dependencies():
    engine = MathEngine()
    engine.set_lines([
        "c = b + 1",
        "b = a * 2",
        "a = 3",
    ])

    assert engine.evaluate("a") == 3
    assert engine.evaluate("b") == 6
    assert engine.evaluate("c") == 7


def test_transitive_dependency_update():
    engine = MathEngine()
    engine.set_lines([
        "a = 2",
        "b = a * 3",
        "c = b + a",
    ])

    engine.update_line(0, "a = 5")

    assert engine.evaluate("b") == 15
    assert engine.evaluate("c") == 20


def test_update_intermediate_dependency():
    engine = MathEngine()
    engine.set_lines([
        "a = 2",
        "b = a + 3",
        "c = b * 2",
    ])

    engine.update_line(1, "b = a + 10")

    assert engine.evaluate("c") == 24


def test_direct_dependency_cycle():
    engine = MathEngine()
    with pytest.raises(Exception):
        engine.set_lines(["a = a + 1"])


def test_indirect_dependency_cycle():
    engine = MathEngine()
    with pytest.raises(Exception):
        engine.set_lines([
            "a = b + 1",
            "b = c + 1",
            "c = a + 1",
        ])


def test_reordering_definitions_preserves_result():
    first = MathEngine()
    first.set_lines(["a = 2", "b = a + 3", "c = b * 2"])

    second = MathEngine()
    second.set_lines(["c = b * 2", "b = a + 3", "a = 2"])

    assert first.evaluate("c") == second.evaluate("c") == 10


def test_removing_used_variable_rolls_back():
    engine = MathEngine()
    engine.set_lines(["a = 2", "b = a + 3"])

    with pytest.raises(Exception):
        engine.remove_line(0)

    assert engine.evaluate("a") == 2
    assert engine.evaluate("b") == 5
    assert engine.lines == ["a = 2", "b = a + 3"]


def test_failed_update_preserves_previous_state():
    engine = MathEngine()
    engine.set_lines(["a = 2", "b = a * 4"])

    with pytest.raises(Exception):
        engine.update_line(0, "a = missing_variable")

    assert engine.evaluate("a") == 2
    assert engine.evaluate("b") == 8
    assert engine.lines == ["a = 2", "b = a * 4"]


def test_failed_set_lines_preserves_previous_state():
    engine = MathEngine()
    engine.set_lines(["a = 4", "b = a + 1"])

    with pytest.raises(Exception):
        engine.set_lines(["x = 10", "y = unknown + 1"])

    assert engine.evaluate("a") == 4
    assert engine.evaluate("b") == 5
    assert engine.lines == ["a = 4", "b = a + 1"]


def test_rebuild_is_idempotent():
    engine = MathEngine()
    engine.set_lines(["a = 2", "b = a * 3", "f(x) = x + a"])

    before = (engine.evaluate("a"), engine.evaluate("b"), engine.call("f", 5))

    engine._rebuild()
    engine._rebuild()

    after = (engine.evaluate("a"), engine.evaluate("b"), engine.call("f", 5))
    assert before == after


def test_global_variable_update_recompiles_function():
    engine = MathEngine()
    engine.set_lines(["a = 2", "f(x) = x * a"])

    assert engine.call("f", 3) == 6

    engine.update_line(0, "a = 5")

    assert engine.call("f", 3) == 15


def test_removed_function_is_not_stale():
    engine = MathEngine()
    engine.set_lines(["f(x) = x + 1"])

    assert engine.call("f", 2) == 3

    engine.set_lines(["a = 10"])

    with pytest.raises(Exception):
        engine.call("f", 2)

    assert engine.evaluate("a") == 10


def test_clear_removes_previous_state():
    engine = MathEngine()
    engine.set_lines(["a = 2", "f(x) = x + a"])

    engine.clear()

    assert engine.get_variable_names() == ()
    assert engine.get_function_names() == ()

    with pytest.raises(Exception):
        engine.evaluate("a")

    with pytest.raises(Exception):
        engine.call("f", 2)


def test_add_line_updates_transitive_dependencies():
    engine = MathEngine()
    engine.set_lines(["a = 2", "b = a + 1"])

    engine.add_line("c = b * 3")

    assert engine.evaluate("c") == 9

    engine.update_line(0, "a = 4")
    assert engine.evaluate("c") == 15


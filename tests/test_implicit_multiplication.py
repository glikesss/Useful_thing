from core.engine import MathEngine


def test_adjacent_letters_are_implicit_multiplication():
    engine = MathEngine()
    engine.set_lines(["a=3", "result=aa"])
    assert engine.get_variable("result") == 9


def test_adjacent_letters_with_exponent_are_implicit_multiplication():
    engine = MathEngine()
    engine.set_lines(["a=3", "result=aa^2"])
    assert engine.get_variable("result") == 81

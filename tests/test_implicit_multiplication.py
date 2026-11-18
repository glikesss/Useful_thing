from core.engine import MathEngine


def test_adjacent_letters_are_implicit_multiplication():
    engine = MathEngine()
    engine.set_lines(["a=3", "result=aa"])
    assert engine.get_variable("result") == 9


def test_adjacent_letters_with_exponent_are_implicit_multiplication():
    engine = MathEngine()
    engine.set_lines(["a=3", "result=aa^2"])
    assert engine.get_variable("result") == 27

 
def test_spaced_adjacent_letters_are_implicit_multiplication():
    engine = MathEngine()
    engine.set_lines(["a=3", "result=a a"])
    assert engine.get_variable("result") == 9


def test_latex_cdot_is_implicit_multiplication():
    engine = MathEngine()
    engine.set_lines(["a=3", r"result=a\cdot a"])
    assert engine.get_variable("result") == 9

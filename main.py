from core import MathEngine


def main():
    engine = MathEngine()

    engine.set_lines([
        "a = 2.5",
        "f(x) = a + x",
        "g(x) = f(x)^2",
        "h(x) = sin(x) + cos(x)",
    ])

    print("Переменные:")

    for name in engine.get_variable_names():
        print(f"  {name} = {engine.get_variable(name)}")

    print("\nФункции:")

    for name in engine.get_function_names():
        print(f"  {name}")

    print("\nВычисления:")

    print("g(3) =", engine.call("g", 3))
    print("h(pi) =", engine.call("h", 3.141592653589793))

    print("\nПроизвольное выражение:")
    print("sqrt(25) + a =", engine.evaluate("sqrt(25) + a"))

    print("\nМатематический анализ:")

    print(
        "f'(3) =",
        engine.differentiate("x^3", "x").subs("x", 3)
    )

    print(
        "f''(3) =",
        engine.differentiate("x^3", "x", 2).subs("x", 3)
    )

    print(
        "Integral x^2 from 0 to 3 =",
        engine.integrate("x^2", "x", 0, 3)
    )

    print(
        "Cumulative integral:",
        engine.cumulative(
            "2*x",
            [0, 1, 2, 3],
            start=0,
        )
    )


if __name__ == "__main__":
    main()
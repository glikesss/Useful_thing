import argparse

from interface import MathLabWindow


def run_demo():
    from core import MathEngine

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
    print("sqrt(25) + a =", engine.evaluate("sqrt(25) + a"))


def main():
    parser = argparse.ArgumentParser(description="MathLab")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the console demonstration instead of the GUI",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable the pywebview debug mode",
    )
    args = parser.parse_args()

    if args.demo:
        run_demo()
    else:
        MathLabWindow(debug=args.debug).run()


if __name__ == "__main__":
    main()

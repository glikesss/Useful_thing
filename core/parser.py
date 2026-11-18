import ast
import re

import numpy as np
from dataclasses import dataclass, field

import sympy as sp

from .errors import ParseError, UnknownNameError

from .calculus import (
    differentiate,
    integrate,
    cumulative_integral,
)

BUILTIN_FUNCTIONS = {
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "sinh": sp.sinh,
    "cosh": sp.cosh,
    "tanh": sp.tanh,
    "sqrt": sp.sqrt,
    "abs": sp.Abs,
    "ln": sp.log,
    "log": sp.log,
    "exp": sp.exp,
}


@dataclass
class VariableDefinition:
    name: str
    expression: sp.Expr
    source: str


@dataclass
class FunctionDefinition:
    name: str
    arguments: tuple[str, ...]
    defaults: dict[str, sp.Expr]
    expression: sp.Expr
    source: str


@dataclass
class ParsedExpression:
    definition: VariableDefinition | FunctionDefinition


class ExpressionParser:
    def __init__(self, file_provider=None):
        self.functions = {}
        self.file_provider = file_provider

    @staticmethod
    def _split_assignment(source: str):
        depth = 0

        for index, char in enumerate(source):
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            elif char == "=" and depth == 0:
                before = source[index - 1] if index else ""
                after = source[index + 1] if index + 1 < len(source) else ""

                if before in "<>=!" or after == "=":
                    continue

                return source[:index].strip(), source[index + 1:].strip()

        return None, source.strip()

    def parse_definition(self, source: str) -> ParsedExpression:
        source = source.strip()

        if not source:
            raise ParseError("Пустое выражение")

        left, right = self._split_assignment(source)

        if left is None:
            raise ParseError(
                "Ожидается определение вида a = выражение"
            )

        if not right:
            raise ParseError("Правая часть выражения пуста")

        try:
            left_ast = ast.parse(left, mode="eval").body
        except SyntaxError as exc:
            raise ParseError(f"Некорректное определение: {exc.msg}") from exc

        if isinstance(left_ast, ast.Name):
            expression = self.parse_expression(right)

            definition = VariableDefinition(
                name=left_ast.id,
                expression=expression,
                source=source,
            )

            return ParsedExpression(definition)

        if isinstance(left_ast, ast.Call):
            return ParsedExpression(
                self._parse_function(left_ast, right, source)
            )

        raise ParseError(
            "Слева от '=' должно быть имя переменной или функции"
        )

    def _parse_function(self, signature, right, source):
        if not isinstance(signature.func, ast.Name):
            raise ParseError("Некорректное имя функции")

        name = signature.func.id

        arguments = []
        defaults = {}

        for argument in signature.args:
            if not isinstance(argument, ast.Name):
                raise ParseError("Аргументы функции должны быть именами")

            arguments.append(argument.id)

        for keyword in signature.keywords:
            if keyword.arg is None:
                raise ParseError("Распаковка аргументов не поддерживается")

            if keyword.arg in arguments:
                raise ParseError(
                    f"Аргумент {keyword.arg} объявлен дважды"
                )

            defaults[keyword.arg] = self.parse_expression(
                ast.unparse(keyword.value)
            )

        all_arguments = arguments + list(defaults)

        if len(set(all_arguments)) != len(all_arguments):
            raise ParseError("Повторяющиеся аргументы функции")

        if not arguments and not defaults:
            raise ParseError("У функции должен быть хотя бы один аргумент")

        symbols = {
            argument: sp.Symbol(argument)
            for argument in all_arguments
        }

        expression = self.parse_expression(
            right,
            local_symbols=symbols,
        )

        return FunctionDefinition(
            name=name,
            arguments=tuple(all_arguments),
            defaults=defaults,
            expression=expression,
            source=source,
        )

    def parse_expression(self, source, local_symbols=None):
        # MathLive may serialize named operators as LaTeX in ASCII output.
        # Normalize file() so it reaches Python's AST as an ordinary function call.
        source = re.sub(
            r"\\(?:operatorname|mathrm|text)\s*\{\s*file\s*\}",
            "file",
            source,
        )
        # MathLive can serialize LaTeX ellipsis as a command or Unicode glyph.
        # Normalize all common forms to Python's Ellipsis token before AST parsing.
        source = re.sub(r"\\(?:ldots|dots|cdots)\b", "...", source)
        source = source.replace("…", "...").replace("⋯", "...")
        source = source.replace("^", "**")
        source = self._insert_implicit_multiplication(source)

        try:
            tree = ast.parse(source, mode="eval")
        except SyntaxError as exc:
            raise ParseError(f"Ошибка синтаксиса: {exc.msg}") from exc

        converter = _ExpressionConverter(
            functions=self.functions,
            local_symbols=local_symbols or {},
            file_provider=self.file_provider,
        )

        try:
            return converter.convert(tree.body)
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError(str(exc)) from exc

    def _insert_implicit_multiplication(self, source):
        """Interpret adjacent single-letter symbols as multiplication (e.g. ax -> a*x)."""
        reserved = (
            set(BUILTIN_FUNCTIONS)
            | set(self.functions)
            | {
                "pi", "e", "range", "linspace", "file",
                "derivative", "integral", "cumulative",
            }
        )
        local_names = set()

        # Keep explicitly declared local symbols intact.
        # Function calls are also preserved, including built-ins.
        token_pattern = re.compile(r"\\b[A-Za-z]+\\b")

        def expand(match):
            name = match.group(0)
            end = match.end()
            remainder = source[end:].lstrip()
            is_call = remainder.startswith("(")

            if (
                len(name) <= 1
                or name in reserved
                or is_call
                or name in local_names
            ):
                return name

            return "*".join(name)

        return token_pattern.sub(expand, source)

    def register_function(self, definition):
        self.functions[definition.name] = definition


class _ExpressionConverter:
    def __init__(self, functions, local_symbols, file_provider=None):
        self.functions = functions
        self.local_symbols = local_symbols
        self.file_provider = file_provider

    @staticmethod
    def _array_operation(operation, left, right):
        try:
            with np.errstate(invalid="raise", divide="raise", over="raise"):
                return operation(left, right)
        except (TypeError, ValueError, FloatingPointError) as exc:
            raise ParseError(f"Ошибка операции с массивами: {exc}") from exc

    def convert(self, node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                raise ParseError("Логические значения не поддерживаются")

            if isinstance(node.value, (int, float)):
                return sp.sympify(node.value)

            raise ParseError("Поддерживаются только числовые константы")

        if isinstance(node, ast.Name):
            if node.id == "pi":
                return sp.pi

            if node.id == "e":
                return sp.E

            if node.id in self.local_symbols:
                return self.local_symbols[node.id]

            return sp.Symbol(node.id)

        if isinstance(node, ast.List | ast.Tuple):
            if not node.elts:
                raise ParseError("Массив не может быть пустым")

            # Синтаксис последовательностей: [1,...,5] или [1,1.1,...,2].
            ellipses = [
                index for index, item in enumerate(node.elts)
                if isinstance(item, ast.Constant) and item.value is Ellipsis
            ]
            if ellipses:
                if len(ellipses) != 1 or len(node.elts) not in (3, 4):
                    raise ParseError(
                        "Синтаксис последовательности: [start,...,stop] "
                        "или [start,next,...,stop]"
                    )
                if ellipses[0] != len(node.elts) - 2:
                    raise ParseError("Многоточие должно находиться перед последним элементом")

                first = self.convert(node.elts[0])
                if not isinstance(first, sp.Number) or first.is_real is not True:
                    raise ParseError("Границы последовательности должны быть числами")
                first = float(sp.N(first))

                if len(node.elts) == 3:
                    start, step = first, 1.0
                else:
                    second = self.convert(node.elts[1])
                    if not isinstance(second, sp.Number) or second.is_real is not True:
                        raise ParseError("Шаг последовательности должен задаваться числами")
                    second = float(sp.N(second))
                    start, step = second, second - first

                stop_value = self.convert(node.elts[-1])
                if not isinstance(stop_value, sp.Number) or stop_value.is_real is not True:
                    raise ParseError("Границы последовательности должны быть числами")
                stop = float(sp.N(stop_value))

                if not all(np.isfinite(value) for value in (first, start, step, stop)):
                    raise ParseError("Последовательность должна содержать конечные числа")
                if step == 0:
                    raise ParseError("Шаг последовательности не может быть равен нулю")
                if (stop - start) * step < 0:
                    raise ParseError("Шаг последовательности направлен от конечной точки")

                count_float = (stop - start) / step
                count = int(np.floor(count_float + 1e-10)) + 1
                if count < 1 or count > 1_000_000:
                    raise ParseError("Последовательность должна содержать от 1 до 1 000 000 элементов")
                result = start + step * np.arange(count, dtype=float)
                tolerance = max(1.0, abs(stop)) * 1e-10
                result = result[result <= stop + tolerance] if step > 0 else result[result >= stop - tolerance]
                if result.size == 0:
                    raise ParseError("Последовательность не содержит элементов")
                if abs(result[-1] - stop) <= tolerance:
                    result[-1] = stop
                return result

            values = [self.convert(item) for item in node.elts]
            try:
                if all(
                    isinstance(value, (int, float, np.number))
                    or (isinstance(value, sp.Number) and value.is_real is True)
                    for value in values
                ):
                    result = np.asarray([float(value) for value in values], dtype=float)
                else:
                    result = np.asarray(values, dtype=object)
            except (TypeError, ValueError) as exc:
                raise ParseError("Массив должен быть прямоугольным") from exc
            if result.ndim != 1:
                raise ParseError("Пока поддерживаются только одномерные массивы")
            return result

        if isinstance(node, ast.Subscript):
            if not isinstance(node.value, ast.Name):
                raise ParseError("Индексировать можно только массив-переменную")
            if isinstance(node.slice, ast.Slice):
                raise ParseError("Срезы массивов пока не поддерживаются")
            index = self.convert(node.slice)
            return sp.IndexedBase(node.value.id)[index - 1]

        if isinstance(node, ast.BinOp):
            left = self.convert(node.left)
            right = self.convert(node.right)

            operations = {
                ast.Add: np.add,
                ast.Sub: np.subtract,
                ast.Mult: np.multiply,
                ast.Div: np.divide,
                ast.Pow: np.power,
                ast.Mod: np.remainder,
            }
            operation = operations.get(type(node.op))
            if operation is None:
                raise ParseError("Неподдерживаемая операция")

            if isinstance(left, np.ndarray) or isinstance(right, np.ndarray):
                return self._array_operation(operation, left, right)
            return operation(left, right)

        if isinstance(node, ast.UnaryOp):
            value = self.convert(node.operand)

            if isinstance(node.op, ast.UAdd):
                return value

            if isinstance(node.op, ast.USub):
                return np.negative(value) if isinstance(value, np.ndarray) else -value

            raise ParseError("Неподдерживаемая унарная операция")

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ParseError("Допускаются только прямые вызовы функций")

            name = node.func.id

            # file() принимает строковый селектор столбца, поэтому
            # обрабатывается до общего преобразования аргументов.
            if name == "file":
                if node.keywords or len(node.args) not in (1, 2):
                    raise ParseError('Синтаксис: file(number) или file(number, "column")')
                if self.file_provider is None:
                    raise ParseError("Функция file() недоступна")
                file_arg = self.convert(node.args[0])
                if isinstance(file_arg, np.ndarray):
                    if file_arg.ndim != 1:
                        raise ParseError("Номера файлов должны быть одномерным массивом")
                    file_numbers = file_arg.tolist()
                else:
                    file_numbers = [file_arg]

                numbers = []
                for value in file_numbers:
                    if not isinstance(value, (int, float, np.number, sp.Number)):
                        raise ParseError("Номер файла должен быть числом")
                    number = float(sp.N(value)) if isinstance(value, sp.Basic) else float(value)
                    if not np.isfinite(number) or not number.is_integer() or number < 1:
                        raise ParseError("Номера файлов должны быть положительными целыми числами")
                    numbers.append(int(number))

                column = None
                if len(node.args) == 2:
                    selector = node.args[1]
                    if isinstance(selector, ast.Constant) and isinstance(selector.value, str):
                        column = selector.value
                    else:
                        column_value = self.convert(selector)
                        if not isinstance(column_value, sp.Number) or column_value.is_real is not True:
                            raise ParseError("Столбец задаётся названием или его номером")
                        column = float(sp.N(column_value))
                        if not column.is_integer() or column < 1:
                            raise ParseError("Номер столбца должен быть положительным целым числом")
                        column = int(column)

                return self.file_provider(numbers, column)

            # Специальные операции математического анализа.
            # Обрабатываем AST непосредственно, чтобы переменная
            # интегрирования не превращалась в обычное выражение.

            if name == "derivative":
                if len(node.args) not in (2, 3) or node.keywords:
                    raise ParseError(
                        "Синтаксис: derivative(f(x), x, order)"
                    )

                expression = self.convert(node.args[0])
                variable_node = node.args[1]

                if not isinstance(variable_node, ast.Name):
                    raise ParseError("Переменная производной должна быть именем")

                order = (
                    self.convert(node.args[2])
                    if len(node.args) == 3
                    else 1
                )

                return differentiate(
                    expression,
                    sp.Symbol(variable_node.id),
                    order,
                )

            if name == "integral":
                if node.keywords or len(node.args) not in (2, 4):
                    raise ParseError(
                        "Синтаксис: integral(f(x), x) "
                        "или integral(f(x), x, a, b)"
                    )

                expression = self.convert(node.args[0])
                variable_node = node.args[1]

                if not isinstance(variable_node, ast.Name):
                    raise ParseError("Переменная интегрирования должна быть именем")

                variable = sp.Symbol(variable_node.id)

                if len(node.args) == 2:
                    return integrate(expression, variable)

                lower = self.convert(node.args[2])
                upper = self.convert(node.args[3])

                return integrate(expression, variable, lower, upper)

            if name == "cumulative":
                if len(node.args) != 3 or node.keywords:
                    raise ParseError(
                        "Синтаксис: cumulative(f(x), x, start)"
                    )

                expression = self.convert(node.args[0])
                variable_node = node.args[1]

                if not isinstance(variable_node, ast.Name):
                    raise ParseError("Переменная интегрирования должна быть именем")

                start = self.convert(node.args[2])

                return cumulative_integral(
                    expression,
                    sp.Symbol(variable_node.id),
                    start,
                )

            # Генерация числовых последовательностей.
            args = [self.convert(arg) for arg in node.args]

            if name == "range":
                if node.keywords or not 1 <= len(args) <= 3:
                    raise ParseError("Синтаксис: range(stop) или range(start, stop, step)")

                values = []
                for argument in args:
                    if not isinstance(argument, sp.Number) or argument.is_real is not True:
                        raise ParseError("Аргументы range должны быть действительными числами")
                    number = float(argument)
                    if not np.isfinite(number) or not number.is_integer():
                        raise ParseError("Аргументы range должны быть целыми числами")
                    values.append(int(number))

                if len(values) == 1:
                    start, stop, step = 0, values[0], 1
                elif len(values) == 2:
                    start, stop = values
                    step = 1
                else:
                    start, stop, step = values

                if step == 0:
                    raise ParseError("Шаг range не может быть равен нулю")
                if len(range(start, stop, step)) > 1_000_000:
                    raise ParseError("Последовательность слишком большая (максимум 1 000 000 элементов)")
                result = np.arange(start, stop, step, dtype=float)
                if result.size == 0:
                    raise ParseError("Последовательность range не может быть пустой")
                return result

            if name == "linspace":
                if node.keywords or len(args) not in (2, 3):
                    raise ParseError("Синтаксис: linspace(start, stop, count)")
                if any(not isinstance(arg, sp.Number) or arg.is_real is not True for arg in args):
                    raise ParseError("Аргументы linspace должны быть действительными числами")
                start, stop = (float(sp.N(arg)) for arg in args[:2])
                count_value = float(sp.N(args[2])) if len(args) == 3 else 50
                if not np.isfinite(count_value) or not count_value.is_integer():
                    raise ParseError("Количество точек linspace должно быть целым числом")
                count = int(count_value)
                if count < 1 or count > 1_000_000:
                    raise ParseError("Количество точек linspace должно быть от 1 до 1 000 000")
                return np.linspace(start, stop, count)

            if name in BUILTIN_FUNCTIONS:
                if node.keywords:
                    raise ParseError("Именованные аргументы не поддерживаются")

                try:
                    if any(isinstance(arg, np.ndarray) for arg in args):
                        numpy_functions = {
                            "sin": np.sin, "cos": np.cos, "tan": np.tan,
                            "asin": np.arcsin, "acos": np.arccos,
                            "atan": np.arctan, "sinh": np.sinh,
                            "cosh": np.cosh, "tanh": np.tanh,
                            "sqrt": np.sqrt, "abs": np.abs,
                            "ln": np.log, "log": np.log10, "exp": np.exp,
                        }
                        return numpy_functions[name](*args)
                    return BUILTIN_FUNCTIONS[name](*args)
                except (TypeError, ValueError, FloatingPointError) as exc:
                    raise ParseError(str(exc)) from exc

            if name in self.functions:
                return self._call_user_function(
                    self.functions[name],
                    args,
                    node.keywords,
                )

            raise UnknownNameError(f"Неизвестная функция: {name}")

        raise ParseError(
            f"Неподдерживаемая конструкция: {type(node).__name__}"
        )


    def _call_user_function(self, definition, args, keywords):
        values = {}

        if len(args) > len(definition.arguments):
            raise ParseError(
                f"Функция {definition.name}: слишком много аргументов"
            )

        for name, value in zip(definition.arguments, args):
            values[name] = value

        for keyword in keywords:
            if keyword.arg not in definition.arguments:
                raise ParseError(
                    f"Неизвестный аргумент: {keyword.arg}"
                )

            if keyword.arg in values:
                raise ParseError(
                    f"Аргумент {keyword.arg} передан дважды"
                )

            values[keyword.arg] = self.convert(keyword.value)

        for name, default in definition.defaults.items():
            values.setdefault(name, default)

        missing = [
            name for name in definition.arguments
            if name not in values
        ]

        if missing:
            raise ParseError(
                f"Не переданы аргументы: {', '.join(missing)}"
            )

        symbols = {
            name: sp.Symbol(name)
            for name in definition.arguments
        }

        substitutions = {
            symbols[name]: value
            for name, value in values.items()
        }

        if any(isinstance(value, np.ndarray) for value in values.values()):
            expression_symbols = sorted(
                definition.expression.free_symbols,
                key=str,
            )
            function = sp.lambdify(
                expression_symbols,
                definition.expression,
                modules=["numpy", "math"],
            )
            arguments = [
                values.get(str(symbol), symbol)
                for symbol in expression_symbols
            ]
            return function(*arguments)

        return definition.expression.subs(substitutions)
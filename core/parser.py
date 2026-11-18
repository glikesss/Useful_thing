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
    def __init__(self):
        self.functions = {}

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
        source = source.replace("^", "**")

        try:
            tree = ast.parse(source, mode="eval")
        except SyntaxError as exc:
            raise ParseError(f"Ошибка синтаксиса: {exc.msg}") from exc

        converter = _ExpressionConverter(
            functions=self.functions,
            local_symbols=local_symbols or {},
        )

        try:
            return converter.convert(tree.body)
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError(str(exc)) from exc

    def register_function(self, definition):
        self.functions[definition.name] = definition


class _ExpressionConverter:
    def __init__(self, functions, local_symbols):
        self.functions = functions
        self.local_symbols = local_symbols

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

            # Обычные аргументы функций.
            args = [self.convert(arg) for arg in node.args]

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
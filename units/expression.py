
import ast
import math
import operator

import numpy as np

from .quantities import Quantity
from .registry import get_unit, is_unit


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_FUNCTIONS = {
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "asin": np.arcsin,
    "acos": np.arccos,
    "atan": np.arctan,
    "sinh": np.sinh,
    "cosh": np.cosh,
    "tanh": np.tanh,
    "sqrt": np.sqrt,
    "abs": np.abs,
    "exp": np.exp,
    "ln": np.log,
    "log": np.log10,
    "log10": np.log10,
}


class QuantityExpressionEvaluator:
    def __init__(self, variables=None, functions=None):
        self.variables = variables or {}
        self.functions = functions or {}

    def evaluate(self, source):
        source = source.replace("^", "**")

        try:
            tree = ast.parse(source, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"Invalid expression: {source}") from exc

        return self._eval(tree.body)

    def _eval(self, node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                raise ValueError("Boolean values are not supported")
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant: {node.value!r}")

        if isinstance(node, ast.Name):
            return self._resolve_name(node.id)

        if isinstance(node, ast.BinOp):
            operation = _BINARY_OPERATORS.get(type(node.op))
            if operation is None:
                raise ValueError("Unsupported binary operator")

            left = self._eval(node.left)
            right = self._eval(node.right)

            return operation(left, right)

        if isinstance(node, ast.UnaryOp):
            operation = _UNARY_OPERATORS.get(type(node.op))
            if operation is None:
                raise ValueError("Unsupported unary operator")

            return operation(self._eval(node.operand))

        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only direct function calls are supported")

            name = node.func.id

            args = [self._eval(arg) for arg in node.args]
            kwargs = {
                keyword.arg: self._eval(keyword.value)
                for keyword in node.keywords
            }

            if name in self.functions:
                return self.functions[name](*args, **kwargs)

            function = _FUNCTIONS.get(name)

            if function is None:
                raise ValueError(f"Unknown function: {name}")

            if kwargs:
                raise ValueError("Keyword arguments are not supported")

            if len(args) != 1:
                raise ValueError(f"{name} expects one argument")

            value = args[0]

            if isinstance(value, Quantity):
                if not value.is_dimensionless:
                    if name == "abs":
                        return abs(value)

                    if name == "sqrt":
                        return value ** 0.5

                    raise ValueError(
                        f"Function {name} requires a dimensionless argument"
                    )

                value = value.value

            result = function(value)

            if isinstance(result, np.ndarray):
                return result.item() if result.ndim == 0 else result

            return float(result)

        raise ValueError(
            f"Unsupported expression element: {type(node).__name__}"
        )

    def _resolve_name(self, name):
        if name in self.variables:
            return self.variables[name]

        if is_unit(name):
            unit = get_unit(name)
            return Quantity(
                unit.scale_to_si,
                unit.dimension,
            )

        if name == "pi":
            return math.pi

        if name == "e":
            return math.e

        raise ValueError(f"Unknown name: {name}")

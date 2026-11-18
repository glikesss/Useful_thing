import sympy as sp
import numpy as np

def _expression_symbols(expression):
    if isinstance(expression, np.ndarray):
        result = set()
        for item in expression.flat:
            result.update(_expression_symbols(item))
        return result
    if isinstance(expression, (list, tuple)):
        result = set()
        for item in expression:
            result.update(_expression_symbols(item))
        return result
    return set(expression.free_symbols) if isinstance(expression, sp.Basic) else set()


def _substitute_expression(expression, substitutions):
    if isinstance(expression, np.ndarray):
        result = np.empty(expression.shape, dtype=object)
        for index, item in np.ndenumerate(expression):
            result[index] = _substitute_expression(item, substitutions)
        return result
    if isinstance(expression, sp.Basic):
        return expression.subs(substitutions)
    return expression


def _numeric_array(expression):
    values = []
    for item in expression.flat:
        if isinstance(item, sp.Basic):
            if item.free_symbols:
                raise EvaluationError("Массив содержит неопределённые переменные")
            item = complex(sp.N(item)) if item.is_real is False else float(sp.N(item))
            if isinstance(item, complex) and item.imag == 0:
                item = item.real
        values.append(item)
    return np.asarray(values).reshape(expression.shape)

def _evaluate_expression(expression, variables):
    if isinstance(expression, sp.Basic) and expression.has(sp.Indexed):
        replacements = {}
        for item in expression.atoms(sp.Indexed):
            name = str(item.base.label)
            array = variables.get(name)
            if not isinstance(array, np.ndarray):
                raise EvaluationError(f"'{name}' не является массивом")
            index_expr = item.indices[0].subs({
                sp.Symbol(key): value
                for key, value in variables.items()
                if isinstance(value, (int, float, np.number))
            })
            if not index_expr.is_number:
                raise EvaluationError("Индекс массива должен быть целым числом")
            numeric_index = float(sp.N(index_expr))
            if not np.isfinite(numeric_index) or not numeric_index.is_integer():
                raise EvaluationError("Индекс массива должен быть целым числом")
            index = int(numeric_index)
            if index < 0 or index >= len(array):
                raise EvaluationError(
                    f"Индекс {index + 1} вне диапазона массива '{name}'"
                )
            replacements[item] = sp.sympify(array[index])
        expression = expression.xreplace(replacements)
        return _evaluate_expression(expression, variables)

    if isinstance(expression, np.ndarray):
        result = _substitute_expression(
            expression,
            {
                sp.Symbol(name): value
                for name, value in variables.items()
                if not isinstance(value, (Quantity, SymbolicQuantity, np.ndarray))
            },
        )
        if _expression_symbols(result):
            return result
        return _numeric_array(result)

    if isinstance(expression, sp.Basic):
        symbols = sorted(expression.free_symbols, key=str)
        if any(isinstance(variables.get(str(symbol)), np.ndarray) for symbol in symbols):
            function = sp.lambdify(symbols, expression, modules=["numpy", "math"])
            result = function(*(variables[str(symbol)] for symbol in symbols))
            if isinstance(result, np.ndarray):
                return np.asarray(result)
            if isinstance(result, sp.Basic) and result.is_number:
                return float(sp.N(result))
            return result
        return expression.subs({
            sp.Symbol(name): value
            for name, value in variables.items()
            if not isinstance(value, (Quantity, SymbolicQuantity, np.ndarray))
        })
    return expression



from .parser import (
    ExpressionParser,
    VariableDefinition,
    FunctionDefinition,
)
from .variables import VariableStore
from .dependencies import topological_sort
from .errors import (
    EvaluationError,
    DependencyError,
)

from .calculus import (
    differentiate,
    integrate,
    numerical_integral,
    numerical_cumulative_integral,
)

from units.expression import QuantityExpressionEvaluator
from units.quantities import Quantity, SymbolicQuantity
from units.registry import is_unit
from .errors import EvaluationError, DimensionError, ParseError

from scipy.integrate import quad

from scipy.integrate import cumulative_trapezoid

class MathEngine:
    def __init__(self, file_provider=None):
        self.lines = []

        self.file_provider = file_provider
        self.parser = ExpressionParser(file_provider=self.file_provider)
        self.variables = VariableStore()
        self.symbolic_variables = {}
        self.external_variables = {}
        self.definitions = {}
        self.functions = {}
        self.compiled_functions = {}

    def set_symbolic_variable(
        self,
        name,
        expression,
        dimension=None,
        symbol_dimensions=None,
    ):
        symbol = sp.Symbol(name)

        quantity = SymbolicQuantity(
            expression=expression,
            dimension=dimension,
            symbol_dimensions=symbol_dimensions or {symbol: dimension}
            if dimension is not None
            else symbol_dimensions or {},
        )

        self.symbolic_variables[name] = quantity
        self.variables.set(name, quantity)

    def remove_symbolic_variable(self, name):
        self.symbolic_variables.pop(name, None)
        self.variables.remove(name)

    # -------------------------------------------------
    # Р РђР‘РћРўРђ РЎ Р¤РћР РњРЈР›РђРњР
    # -------------------------------------------------

    def add_line(self, source):
        self.lines.append(source)

        try:
            self._rebuild()
        except Exception:
            self.lines.pop()
            self._rebuild()
            raise

        return len(self.lines) - 1

    def update_line(self, index, source):
        old_source = self.lines[index]
        self.lines[index] = source

        try:
            self._rebuild()
        except Exception:
            self.lines[index] = old_source
            self._rebuild()
            raise

    def remove_line(self, index):
        old_source = self.lines.pop(index)

        try:
            self._rebuild()
        except Exception:
            self.lines.insert(index, old_source)
            self._rebuild()
            raise

    def set_lines(self, sources):
        old_lines = self.lines
        self.lines = list(sources)

        try:
            self._rebuild()
        except Exception:
            self.lines = old_lines
            self._rebuild()
            raise

    def clear(self):
        self.lines.clear()
        self._rebuild()


    # -------------------------------------------------
    # РџР•Р Р•РЎР‘РћР РљРђ РЇР”Р Рђ
    # -------------------------------------------------

    def set_file_provider(self, provider):
        self.file_provider = provider
        self.parser = ExpressionParser(file_provider=provider)
        self._rebuild()

    def _rebuild(self):
        self.parser = ExpressionParser(file_provider=self.file_provider)

        self.variables.clear()
        self.variables.update(self.symbolic_variables)
        self.definitions.clear()
        self.functions.clear()
        self.compiled_functions.clear()

        # РЎРЅР°С‡Р°Р»Р° СЂР°Р·Р±РёСЂР°РµРј РІСЃРµ СЃС‚СЂРѕРєРё.
        # РџРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёРµ С„СѓРЅРєС†РёРё РґРѕР»Р¶РЅС‹ Р±С‹С‚СЊ РѕР±СЉСЏРІР»РµРЅС‹
        # РґРѕ РїРµСЂРІРѕРіРѕ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёСЏ.
        for source in self.lines:
            parsed = self.parser.parse_definition(source)
            definition = parsed.definition

            if definition.name in self.definitions:
                raise EvaluationError(
                    f"РРјСЏ '{definition.name}' РѕРїСЂРµРґРµР»РµРЅРѕ РїРѕРІС‚РѕСЂРЅРѕ"
                )

            self.definitions[definition.name] = definition

            if isinstance(definition, FunctionDefinition):
                self.functions[definition.name] = definition
                self.parser.register_function(definition)

        self._calculate_variables()
        self._compile_functions()

    # -------------------------------------------------
    # Р’Р«Р§РРЎР›Р•РќРР• РџР•Р Р•РњР•РќРќР«РҐ
    # -------------------------------------------------

        
    def _calculate_variables(self):
        variable_definitions = {
            name: definition
            for name, definition in self.definitions.items()
            if isinstance(definition, VariableDefinition)
        }

        variable_names = set(variable_definitions)
        graph = {}

        for name, definition in variable_definitions.items():
            dependencies = {
                str(symbol)
                for symbol in _expression_symbols(definition.expression)
                if str(symbol) in variable_names
            }
            graph[name] = dependencies

        order = topological_sort(graph)
        resolved = dict(self.external_variables)

        for name in order:
            definition = variable_definitions[name]
            expression = definition.expression

            dependencies = {
                str(symbol)
                for symbol in _expression_symbols(expression)
                if str(symbol) in resolved
            }

            has_quantity_dependency = any(
                isinstance(resolved[dep], Quantity)
                for dep in dependencies
            )

            has_unit = any(
                is_unit(str(symbol))
                and str(symbol) not in resolved
                for symbol in _expression_symbols(expression)
            )

            try:
                if has_quantity_dependency or has_unit:
                    _, source_expression = self.parser._split_assignment(
                        definition.source
                    )

                    evaluator = QuantityExpressionEvaluator(
                        variables=resolved
                    )
                    value = evaluator.evaluate(source_expression)

                else:
                    expression = _evaluate_expression(expression, resolved)

                    remaining = _expression_symbols(expression)
                    if remaining:
                        unknown = sorted(str(symbol) for symbol in remaining)
                        raise EvaluationError(
                            f"Неопределённые переменные в '{name}': "
                            + ", ".join(unknown)
                        )

                    if isinstance(expression, sp.Basic):
                        value = sp.N(expression)
                        if value.is_real is False:
                            raise EvaluationError(
                                f"Переменная '{name}' имеет комплексное значение"
                            )
                        if value.is_number:
                            value = float(value)
                    else:
                        value = expression

                resolved[name] = value

            except (EvaluationError, DimensionError):
                raise

            except Exception as exc:
                raise EvaluationError(
                    f"РќРµ СѓРґР°Р»РѕСЃСЊ РІС‹С‡РёСЃР»РёС‚СЊ '{name}': {exc}"
                ) from exc

        self.variables.update(resolved)


    # -------------------------------------------------
    # РљРћРњРџРР›РЇР¦РРЇ РџРћР›Р¬Р—РћР’РђРўР•Р›Р¬РЎРљРРҐ Р¤РЈРќРљР¦РР™
    # -------------------------------------------------

    
    def _compile_functions(self):
        self.compiled_functions = {}

        global_values = {
            sp.Symbol(name): value
            for name, value in self.variables.as_dict().items()
            if not isinstance(value, (Quantity, SymbolicQuantity, np.ndarray))
        }

        known_globals = {
            sp.Symbol(name)
            for name in self.variables.as_dict()
        }

        for name, definition in self.functions.items():
            argument_symbols = {
                sp.Symbol(str(argument))
                for argument in definition.arguments
            }

            for argument, default in definition.defaults.items():
                unresolved = (
                    default.free_symbols
                    - known_globals
                    - argument_symbols
                )

                if unresolved:
                    names = ", ".join(
                        sorted(str(symbol) for symbol in unresolved)
                    )
                    raise EvaluationError(
                        f"Unknown symbol(s) in default argument "
                        f"'{argument}' of function '{name}': {names}"
                    )

            expression = definition.expression.subs(global_values)

            self.compiled_functions[name] = sp.lambdify(
                definition.arguments,
                expression,
                modules=["numpy", "math"],
            )

    # -------------------------------------------------
    # Р’Р«Р§РРЎР›Р•РќРР• РџР РћРР—Р’РћР›Р¬РќРћР“Рћ Р’Р«Р РђР–Р•РќРРЇ
    # -------------------------------------------------

    def _evaluate_symbolic_expression(self, expression, variables):
        if expression.is_Number:
            return expression

        if expression.is_Symbol:
            name = str(expression)
            return variables.get(name, expression)

        if expression.is_Add:
            args = [
                self._evaluate_symbolic_expression(arg, variables)
                for arg in expression.args
            ]

            result = args[0]

            for arg in args[1:]:
                result = result + arg

            return result

        if expression.is_Mul:
            args = [
                self._evaluate_symbolic_expression(arg, variables)
                for arg in expression.args
            ]

            result = args[0]

            for arg in args[1:]:
                result = result * arg

            return result

        if expression.is_Pow:
            base = self._evaluate_symbolic_expression(
                expression.base, variables
            )
            exponent = self._evaluate_symbolic_expression(
                expression.exp, variables
            )

            return base ** exponent

        if expression.is_Function:
            args = [
                self._evaluate_symbolic_expression(arg, variables)
                for arg in expression.args
            ]

            if any(isinstance(arg, SymbolicQuantity) for arg in args):
                if expression.func == sp.Abs:
                    return abs(args[0])

                if any(
                    isinstance(arg, SymbolicQuantity)
                    and not arg.dimension.is_dimensionless
                    for arg in args
                ):
                    raise DimensionError(
                        f"Function {expression.func} requires "
                        "dimensionless arguments"
                    )

                raw_args = [
                    arg.expression
                    if isinstance(arg, SymbolicQuantity)
                    else arg
                    for arg in args
                ]

                return SymbolicQuantity(
                    expression.func(*raw_args),
                    symbol_dimensions=self._merge_symbol_dimensions(args),
                )

            return expression.func(*args)

        return expression

    @staticmethod
    def _merge_symbol_dimensions(values):
        result = {}

        for value in values:
            if isinstance(value, SymbolicQuantity):
                result = SymbolicQuantity._merge_dimensions(
                    result,
                    value.symbol_dimensions,
                )

        return result

    def evaluate(self, source):
        try:
            expression = self.parser.parse_expression(source)

            symbols = {str(symbol) for symbol in _expression_symbols(expression)}

            variables = self.variables.as_dict()

            has_symbolic_quantity = any(
                isinstance(variables.get(name), SymbolicQuantity)
                for name in symbols
            )

            if has_symbolic_quantity:
                result = self._evaluate_symbolic_expression(
                    expression,
                    variables,
                )

                if isinstance(result, SymbolicQuantity):
                    return result

                if result.free_symbols:
                    unknown = sorted(
                        str(symbol)
                        for symbol in result.free_symbols
                    )
                    raise EvaluationError(
                        "РќРµРёР·РІРµСЃС‚РЅС‹Рµ РїРµСЂРµРјРµРЅРЅС‹Рµ: " + ", ".join(unknown)
                    )

                return result

            has_quantity = any(
                isinstance(variables.get(name), Quantity)
                for name in symbols
            )

            has_unit = any(
                is_unit(name) and name not in variables
                for name in symbols
            )

            # Р¤РёР·РёС‡РµСЃРєРёРµ РІС‹СЂР°Р¶РµРЅРёСЏ РѕР±СЂР°Р±Р°С‚С‹РІР°РµРј Р”Рћ SymPy-РїРѕРґСЃС‚Р°РЅРѕРІРѕРє.
            if has_quantity or has_unit:
                return QuantityExpressionEvaluator(
                    variables=variables,
                    functions=self._quantity_function_callbacks(),
                ).evaluate(source)

            # РћР±С‹С‡РЅС‹Р№ РїСѓС‚СЊ SymPy.
            substitutions = {
                sp.Symbol(name): value
                for name, value in variables.items()
                if not isinstance(value, Quantity)
            }

            expression = _evaluate_expression(expression, variables)

            remaining = _expression_symbols(expression)
            if remaining:
                unknown = sorted(str(symbol) for symbol in remaining)
                raise EvaluationError(
                    "Неизвестные переменные: " + ", ".join(unknown)
                )

            if isinstance(expression, np.ndarray):
                return expression

            if isinstance(expression, sp.Basic) and expression.is_number:
                return float(sp.N(expression))

            return expression

        except (EvaluationError, DimensionError):
            raise

        except Exception as exc:
            raise EvaluationError(str(exc)) from exc

    # -------------------------------------------------
    # Р’Р«Р—РћР’ РџРћР›Р¬Р—РћР’РђРўР•Р›Р¬РЎРљРћР™ Р¤РЈРќРљР¦РР
    # -------------------------------------------------



    def call(self, name, *args, **kwargs):
        if name not in self.functions:
            raise EvaluationError(f"Unknown function: {name}")

        definition = self.functions[name]
        argument_names = [str(arg) for arg in definition.arguments]
        defaults = {
            str(key): value
            for key, value in definition.defaults.items()
        }

        if len(args) > len(argument_names):
            raise EvaluationError(
                f"Too many arguments for function '{name}'"
            )

        provided = dict(zip(argument_names, args))

        for key, value in kwargs.items():
            if key not in argument_names:
                raise EvaluationError(
                    f"Unknown argument '{key}' for function '{name}'"
                )

            if key in provided:
                raise EvaluationError(
                    f"Multiple values for argument '{key}'"
                )

            provided[key] = value

        ordered_args = []

        global_values = {
            sp.Symbol(key): value
            for key, value in self.variables.as_dict().items()
            if not isinstance(value, (Quantity, SymbolicQuantity, np.ndarray))
        }

        for argument in argument_names:
            if argument in provided:
                value = provided[argument]

            elif argument in defaults:
                value = defaults[argument]

                if isinstance(value, sp.Basic):
                    value = value.subs(global_values)

                    if value.free_symbols:
                        raise EvaluationError(
                            f"Unresolved default argument '{argument}' "
                            f"in function '{name}'"
                        )

                    if value.is_number:
                        value = float(sp.N(value))

            else:
                raise EvaluationError(
                    f"Missing argument '{argument}' for function '{name}'"
                )

            ordered_args.append(value)


        global_variables = self.variables.as_dict()

        has_symbolic_argument = any(
            isinstance(value, SymbolicQuantity)
            for value in ordered_args
        )

        has_symbolic_global = any(
            isinstance(global_variables.get(str(symbol)), SymbolicQuantity)
            for symbol in _expression_symbols(definition.expression)
        )

        if has_symbolic_argument or has_symbolic_global:
            symbolic_variables = dict(global_variables)
            symbolic_variables.update(
                dict(zip(argument_names, ordered_args))
            )

            return self._evaluate_symbolic_expression(
                definition.expression,
                symbolic_variables,
            )

        has_quantity_argument = any(
            isinstance(value, Quantity)
            for value in ordered_args
        )

        has_quantity_global = any(
            isinstance(global_variables.get(str(symbol)), Quantity)
            for symbol in _expression_symbols(definition.expression)
        )

        if has_quantity_argument or has_quantity_global:
            return self._quantity_function(name, *ordered_args)



        try:
            for index, value in enumerate(ordered_args):
                try:
                    finite = np.all(np.isfinite(value))
                except (TypeError, ValueError):
                    continue

                if not bool(finite):
                    raise EvaluationError(
                        f"Non-finite argument '{argument_names[index]}' "
                        f"in function '{name}'"
                    )

            with np.errstate(
                invalid="raise",
                divide="raise",
                over="raise",
            ):
                result = self.compiled_functions[name](*ordered_args)

            try:
                finite = np.all(np.isfinite(result))
            except (TypeError, ValueError):
                finite = True

            if not bool(finite):
                raise EvaluationError(
                    f"Non-finite result from function '{name}'"
                )

            return result

        except EvaluationError:
            raise
        except Exception as exc:
            raise EvaluationError(
                f"Numerical error in function '{name}': {exc}"
            ) from exc


    # -------------------------------------------------
    # РњРђРўР•РњРђРўРР§Р•РЎРљРР™ РђРќРђР›РР—
    # -------------------------------------------------

    def _prepare_calculus_expression(self, source):
        expression = self.parser.parse_expression(source)

        substitutions = {
            sp.Symbol(name): value
            for name, value in self.variables.as_dict().items()
        }

        return expression.subs(substitutions)


    def differentiate(self, source, variable, order=1):
        try:
            expression = self.parser.parse_expression(source)

            variable_name = str(variable)
            variable_symbol = sp.Symbol(variable_name)

            # РЎРЅР°С‡Р°Р»Р° РґРёС„С„РµСЂРµРЅС†РёСЂСѓРµРј СЃРёРјРІРѕР»РёС‡РµСЃРєРѕРµ РІС‹СЂР°Р¶РµРЅРёРµ.
            result = differentiate(
                expression,
                variable_symbol,
                order,
            )

            variables = self.variables.as_dict()

            has_symbolic_quantity = any(
                isinstance(variables.get(str(symbol)), SymbolicQuantity)
                for symbol in _expression_symbols(expression)
            )

            if has_symbolic_quantity:
                symbolic_expression = self._evaluate_symbolic_expression(
                    expression,
                    variables,
                )

                if isinstance(symbolic_expression, SymbolicQuantity):
                    return symbolic_expression.diff(
                        variable_symbol,
                        order,
                    )

            # РћРїСЂРµРґРµР»СЏРµРј, С‚СЂРµР±СѓРµС‚СЃСЏ Р»Рё С„РёР·РёС‡РµСЃРєРѕРµ РІС‹С‡РёСЃР»РµРЅРёРµ.
            has_quantity = any(
                isinstance(variables.get(str(symbol)), Quantity)
                for symbol in result.free_symbols
            )

            has_unit = any(
                is_unit(str(symbol))
                and str(symbol) not in variables
                for symbol in result.free_symbols
            )

            if has_quantity or has_unit:
                evaluator = QuantityExpressionEvaluator(
                    variables=variables,
                    functions=self._quantity_function_callbacks(),
                )

                return evaluator.evaluate(str(result))

            # РћР±С‹С‡РЅС‹Р№ РїСѓС‚СЊ SymPy.
            substitutions = {
                sp.Symbol(name): value
                for name, value in variables.items()
                if not isinstance(value, (Quantity, SymbolicQuantity, np.ndarray))
                and name != variable_name
            }

            result = result.subs(substitutions)

            if not result.free_symbols and result.is_number:
                return float(sp.N(result))

            return result

        except DimensionError:
            raise

        except ParseError:
            raise

        except (EvaluationError, DimensionError):
            raise

        except Exception as exc:
            raise EvaluationError(str(exc)) from exc


    
    def integrate(
        self,
        source,
        variable="x",
        lower=None,
        upper=None,
        numerical=True,
    ):
        try:
            expression = self.parser.parse_expression(source)
            symbol = sp.Symbol(variable)
            variables = self.variables.as_dict()

            has_symbolic_quantity = any(
                isinstance(variables.get(str(item)), SymbolicQuantity)
                for item in _expression_symbols(expression)
            )

            if has_symbolic_quantity:
                symbolic_expression = self._evaluate_symbolic_expression(
                    expression,
                    variables,
                )

                if isinstance(symbolic_expression, SymbolicQuantity):
                    return symbolic_expression.integrate(
                        symbol,
                        lower,
                        upper,
                    )

            if lower is None and upper is None:
                return integrate(expression, symbol)

            if lower is None or upper is None:
                raise ParseError(
                    "РќРµРѕР±С…РѕРґРёРјРѕ СѓРєР°Р·Р°С‚СЊ РѕР±Р° РїСЂРµРґРµР»Р° РёРЅС‚РµРіСЂРёСЂРѕРІР°РЅРёСЏ"
                )

            # РћРїСЂРµРґРµР»СЏРµРј, С‚СЂРµР±СѓРµС‚СЃСЏ Р»Рё С„РёР·РёС‡РµСЃРєРѕРµ РІС‹С‡РёСЃР»РµРЅРёРµ.
            has_quantity = any(
                isinstance(variables.get(str(item)), Quantity)
                for item in _expression_symbols(expression)
            )

            has_unit = any(
                is_unit(str(item)) and str(item) not in variables
                for item in _expression_symbols(expression)
            )

            physical_bounds = (
                isinstance(lower, Quantity)
                or isinstance(upper, Quantity)
            )

            if not (has_quantity or has_unit or physical_bounds):
                lower = float(lower)
                upper = float(upper)

                result = integrate(
                    expression,
                    symbol,
                    lower,
                    upper,
                )

                if not result.has(sp.Integral):
                    return float(sp.N(result))

                if not numerical:
                    return result

                return numerical_integral(
                    expression,
                    symbol,
                    lower,
                    upper,
                )

            # Р¤РёР·РёС‡РµСЃРєРёР№ РїСѓС‚СЊ.
            if isinstance(lower, Quantity) != isinstance(upper, Quantity):
                raise DimensionError(
                    "РћР±Р° РїСЂРµРґРµР»Р° РґРѕР»Р¶РЅС‹ РёРјРµС‚СЊ РѕРґРёРЅР°РєРѕРІС‹Р№ С‚РёРї"
                )

            if isinstance(lower, Quantity):
                if lower.dimension != upper.dimension:
                    raise DimensionError(
                        "Р Р°Р·РјРµСЂРЅРѕСЃС‚Рё РїСЂРµРґРµР»РѕРІ РёРЅС‚РµРіСЂРёСЂРѕРІР°РЅРёСЏ РЅРµСЃРѕРІРјРµСЃС‚РёРјС‹"
                    )

                lower_value = float(lower.value)
                upper_value = float(upper.value)
                variable_dimension = lower.dimension
            else:
                lower_value = float(lower)
                upper_value = float(upper)
                variable_dimension = None

            evaluator = QuantityExpressionEvaluator(
                variables=variables,
                functions=self._quantity_function_callbacks(),
            )

            integrand_dimension = None

            def integrand(value):
                nonlocal integrand_dimension

                if variable_dimension is None:
                    variable_value = value
                else:
                    variable_value = Quantity(
                        value,
                        variable_dimension,
                    )

                local_evaluator = QuantityExpressionEvaluator(
                    variables={
                        **variables,
                        variable: variable_value,
                    },
                    functions=self._quantity_function_callbacks(),
                )

                result = local_evaluator.evaluate(source)

                if isinstance(result, Quantity):
                    if integrand_dimension is None:
                        integrand_dimension = result.dimension
                    elif integrand_dimension != result.dimension:
                        raise DimensionError(
                            "Р Р°Р·РјРµСЂРЅРѕСЃС‚СЊ РїРѕРґС‹РЅС‚РµРіСЂР°Р»СЊРЅРѕРіРѕ РІС‹СЂР°Р¶РµРЅРёСЏ РёР·РјРµРЅРёР»Р°СЃСЊ"
                        )

                    return float(result.value)

                if integrand_dimension is None:
                    integrand_dimension = None

                return float(result)

            result_value, _ = quad(
                integrand,
                lower_value,
                upper_value,
            )

            if integrand_dimension is None:
                if variable_dimension is None:
                    return float(result_value)

                return Quantity(
                    result_value,
                    variable_dimension,
                )

            if variable_dimension is not None:
                result_dimension = (
                    integrand_dimension * variable_dimension
                )
            else:
                result_dimension = integrand_dimension

            return Quantity(
                result_value,
                result_dimension,
            )

        except (ParseError, EvaluationError, DimensionError):
            raise

        except Exception as exc:
            raise EvaluationError(str(exc)) from exc


    def cumulative(
        self,
        source,
        values,
        variable="x",
        start=0,
    ):
        try:
            expression = self.parser.parse_expression(source)
            symbol = sp.Symbol(variable)
            variables = self.variables.as_dict()

            values = list(values)

            # ??????????? ????????????? ?????????? ??????????????.
            symbolic_coordinate = variables.get(variable)
            symbolic_coordinate_dimension = (
                symbolic_coordinate.symbol_dimensions.get(symbol)
                if isinstance(symbolic_coordinate, SymbolicQuantity)
                else None
            )

            has_quantity = any(
                isinstance(variables.get(str(item)), Quantity)
                for item in _expression_symbols(expression)
            )

            has_unit = any(
                is_unit(str(item)) and str(item) not in variables
                for item in _expression_symbols(expression)
            )

            has_quantity_coordinates = (
                isinstance(start, Quantity)
                or any(isinstance(value, Quantity) for value in values)
            )

            has_symbolic_coordinate = (
                symbolic_coordinate_dimension is not None
            )

            if not (
                has_quantity
                or has_unit
                or has_quantity_coordinates
                or has_symbolic_coordinate
            ):
                return numerical_cumulative_integral(
                    expression,
                    symbol,
                    start,
                    values,
                    parameters={
                        name: value
                        for name, value in variables.items()
                        if not isinstance(value, (Quantity, SymbolicQuantity, np.ndarray))
                    },
                )

            # ?????????? ??????????? ??????????.
            coordinate_quantities = [
                value
                for value in [start, *values]
                if isinstance(value, Quantity)
            ]

            coordinate_dimension = (
                coordinate_quantities[0].dimension
                if coordinate_quantities
                else symbolic_coordinate_dimension
            )

            if (
                symbolic_coordinate_dimension is not None
                and coordinate_dimension != symbolic_coordinate_dimension
            ):
                raise DimensionError(
                    "??????????? ????????? ?? ????????? "
                    "? ???????????? ????????????? ??????????"
                )

            for value in coordinate_quantities:
                if value.dimension != coordinate_dimension:
                    raise DimensionError(
                        "??????????? ????????? ?????????????? ????????????"
                    )

            def numeric_value(value):
                if isinstance(value, Quantity):
                    return float(value.value)
                return float(value)

            start_value = numeric_value(start)

            numeric_values = np.asarray(
                [numeric_value(value) for value in values],
                dtype=float,
            )

            if not np.all(np.isfinite(numeric_values)):
                raise EvaluationError(
                    "?????? ???????? NaN ??? ??????????? ????????"
                )

            grid = np.concatenate(([start_value], numeric_values))
            differences = np.diff(grid)

            if not (
                np.all(differences >= 0)
                or np.all(differences <= 0)
            ):
                raise EvaluationError(
                    "???????? ?????????? ?????? ???? ? ?????????? ???????"
                )

            initial_variables = {
                **variables,
                variable: (
                    Quantity(start_value, coordinate_dimension)
                    if coordinate_dimension is not None
                    else start_value
                ),
            }

            initial_evaluator = QuantityExpressionEvaluator(
                variables=initial_variables,
                functions=self._quantity_function_callbacks(),
            )

            initial_result = initial_evaluator.evaluate(source)

            integrand_dimension = (
                initial_result.dimension
                if isinstance(initial_result, Quantity)
                else None
            )

            local_variables = {
                **variables,
                variable: (
                    Quantity(grid, coordinate_dimension)
                    if coordinate_dimension is not None
                    else grid
                ),
            }

            evaluator = QuantityExpressionEvaluator(
                variables=local_variables,
                functions=self._quantity_function_callbacks(),
            )

            result = evaluator.evaluate(source)

            if isinstance(result, Quantity):
                if (
                    integrand_dimension is not None
                    and result.dimension != integrand_dimension
                ):
                    raise DimensionError(
                        "??????????? ????????? ??????????"
                    )

                integrand_values = np.asarray(
                    result.value,
                    dtype=float,
                )
            else:
                integrand_values = np.asarray(result, dtype=float)

            if integrand_values.ndim == 0:
                integrand_values = np.full(
                    len(grid),
                    float(integrand_values),
                )

            if not np.all(np.isfinite(integrand_values)):
                raise EvaluationError(
                    "??????????????? ??????? ??????? NaN ??? ?????????????"
                )

            if len(integrand_values) != len(grid):
                raise EvaluationError(
                    "?????????? ???????? ??????? ?? ????????? "
                    "? ??????????? ?????????"
                )

            integrated_values = cumulative_trapezoid(
                integrand_values,
                x=grid,
                initial=0.0,
            )

            result_dimension = integrand_dimension

            if coordinate_dimension is not None:
                if result_dimension is None:
                    result_dimension = coordinate_dimension
                else:
                    result_dimension = (
                        result_dimension * coordinate_dimension
                    )

            if result_dimension is None:
                return integrated_values

            return Quantity(
                integrated_values[1:],
                result_dimension,
            )

        except (ParseError, EvaluationError, DimensionError):
            raise

        except Exception as exc:
            raise EvaluationError(str(exc)) from exc
    def set_external_variable(self, name, value):
        """Register an externally supplied value that survives formula rebuilds."""
        old_value = self.external_variables.get(name)
        existed = name in self.external_variables
        self.external_variables[name] = value
        try:
            self._rebuild()
        except Exception:
            if existed:
                self.external_variables[name] = old_value
            else:
                self.external_variables.pop(name, None)
            self._rebuild()
            raise

    def get_variable(self, name):
        if not self.variables.has(name):
            raise EvaluationError(
                f"РџРµСЂРµРјРµРЅРЅР°СЏ '{name}' РЅРµ РЅР°Р№РґРµРЅР°"
            )

        return self.variables.get(name)

    def get_function_names(self):
        return tuple(self.functions.keys())

    def get_variable_names(self):
        return self.variables.names()

    def get_definition(self, name):
        return self.definitions.get(name)

        
    def _quantity_function(self, name, *args, **kwargs):
        if name not in self.functions:
            raise EvaluationError(f"Unknown function: {name}")

        definition = self.functions[name]
        argument_names = list(definition.arguments)

        if len(args) > len(argument_names):
            raise EvaluationError(
                f"Too many arguments for function '{name}'"
            )

        local_variables = dict(zip(argument_names, args))

        for key, value in kwargs.items():
            if key not in argument_names:
                raise EvaluationError(
                    f"Unknown argument '{key}' for function '{name}'"
                )

            if key in local_variables:
                raise EvaluationError(
                    f"Multiple values for argument '{key}'"
                )

            local_variables[key] = value

        evaluator = QuantityExpressionEvaluator(
            variables=self.variables.as_dict(),
            functions=self._quantity_function_callbacks(),
        )

        for argument in argument_names:
            if argument not in local_variables:
                if argument not in definition.defaults:
                    raise EvaluationError(
                        f"Missing argument '{argument}' "
                        f"for function '{name}'"
                    )

                default = definition.defaults[argument]

                if isinstance(default, sp.Expr):
                    default = evaluator.evaluate(str(default))

                local_variables[argument] = default

        _, source = self.parser._split_assignment(definition.source)

        evaluator.variables.update(local_variables)

        return evaluator.evaluate(source)


    def _quantity_function_callbacks(self):
        return {
            name: (
                lambda *args, _name=name, **kwargs:
                self._quantity_function(_name, *args, **kwargs)
            )
            for name in self.functions
        }

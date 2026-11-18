class MathLabError(Exception):
    """Базовая ошибка MathLab."""


class ParseError(MathLabError):
    """Ошибка синтаксиса выражения."""


class EvaluationError(MathLabError):
    """Ошибка вычисления."""


class DependencyError(MathLabError):
    """Ошибка зависимостей между выражениями."""


class UnknownNameError(ParseError):
    """Неизвестная функция или некорректное обращение к имени."""


class DimensionError(MathLabError):
    """Ошибка физической размерности."""
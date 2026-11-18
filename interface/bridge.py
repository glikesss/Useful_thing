import base64
from io import BytesIO
from pathlib import Path
from threading import RLock

import matplotlib
import numpy as np
matplotlib.use("Agg", force=True)
import pandas as pd
from sympy.printing.mathml import mathml as sympy_mathml

from core import MathEngine
from data import DataManager, load_csv_file
from data.csv_loader import save_csv_file
from data.processing import derivative, filter_rows, integrate, smooth, statistics
from plotting import PlotManager


class MathLabBridge:
    """Python API exposed to the pywebview frontend."""

    def __init__(self):
        self.engine = MathEngine()
        self.data_manager = DataManager()
        self._window = None
        self._lock = RLock()

    def _set_window(self, window):
        self._window = window

    @staticmethod
    def _format_value(value):
        return str(value)

    @staticmethod
    def _json_value(value):
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass

        if hasattr(value, "item"):
            value = value.item()

        if isinstance(value, (str, int, float, bool)) or value is None:
            return value

        return str(value)

    @staticmethod
    def _is_numeric_column(series):
        values = series.dropna().astype("string").str.strip()
        values = values[values != ""]

        if values.empty:
            return False

        values = values.str.replace(",", ".", regex=False)
        numeric = pd.to_numeric(values, errors="coerce")
        return numeric.notna().sum() >= max(1, int(len(values) * 0.9))

    def _dataset_info(self, name):
        frame = self.data_manager.get_data(name, copy=False)
        return {
            "name": name,
            "rows": len(frame),
            "columns": [str(column) for column in frame.columns],
            "numeric_columns": [
                str(column)
                for column in frame.columns
                if self._is_numeric_column(frame[column])
            ],
        }

    @staticmethod
    def _expression_mathml(expression):
        """Render a SymPy expression as presentation MathML for the UI."""
        try:
            body = sympy_mathml(expression, printer="presentation")
            if body.startswith("<math"):
                return body
            return (
                '<math xmlns="http://www.w3.org/1998/Math/MathML">'
                f"{body}</math>"
            )
        except Exception:
            return None

    def _build_state(self):
        variables = [
            {
                "name": name,
                "value": self._format_value(self.engine.get_variable(name)),
            }
            for name in self.engine.get_variable_names()
        ]
        formulas = [
            {
                "name": name,
                "source": definition.source,
                "mathml": self._expression_mathml(definition.expression),
            }
            for name, definition in self.engine.definitions.items()
        ]
        return {
            "lines": list(self.engine.lines),
            "formulas": formulas,
            "variables": variables,
            "functions": list(self.engine.get_function_names()),
            "arrays": [
                name for name in self.engine.get_variable_names()
                if isinstance(self.engine.get_variable(name), np.ndarray)
            ],
            "datasets": [
                self._dataset_info(name)
                for name in self.data_manager.list_datasets()
            ],
        }

    def get_state(self):
        with self._lock:
            return self._build_state()

    def preview_formula(self, source):
        """Preview one formula without applying or changing engine state."""
        try:
            if not isinstance(source, str) or not source.strip():
                raise ValueError("Введите формулу")
            with self._lock:
                parsed = self.engine.parser.parse_definition(source.strip())
                mathml = self._expression_mathml(parsed.definition.expression)
            if not mathml:
                raise ValueError("Не удалось построить математическое представление")
            return {"ok": True, "mathml": mathml}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def set_lines(self, lines):
        try:
            if not isinstance(lines, (list, tuple)):
                raise TypeError("lines must be a list of strings")
            if any(not isinstance(line, str) for line in lines):
                raise TypeError("Every formula must be a string")

            cleaned = [line.strip() for line in lines if line.strip()]

            with self._lock:
                self.engine.set_lines(cleaned)
                return {
                    "ok": True,
                    "state": self._build_state(),
                    "message": "Формулы применены",
                }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def evaluate(self, expression):
        try:
            if not isinstance(expression, str) or not expression.strip():
                raise ValueError("Введите выражение")
            with self._lock:
                result = self.engine.evaluate(expression)
            return {"ok": True, "result": self._format_value(result)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def call_function(self, name, args=None):
        try:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Имя функции не задано")
            if args is None:
                args = []
            if not isinstance(args, list):
                raise TypeError("args must be a list")
            with self._lock:
                result = self.engine.call(name, *args)
            return {"ok": True, "result": self._format_value(result)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def load_csv(self, path, name=None):
        try:
            path = Path(path)
            if not name:
                name = path.stem
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Введите имя набора данных")
            name = name.strip()

            with self._lock:
                if name in self.data_manager:
                    raise ValueError(f"Набор данных уже существует: {name}")
                frame = load_csv_file(path)
                self.data_manager.add_data(name, frame)
                return {
                    "ok": True,
                    "dataset": self._dataset_info(name),
                    "state": self._build_state(),
                    "message": f"Загружено: {path.name}",
                }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def select_csv_file(self, name=None):
        try:
            if self._window is None:
                raise RuntimeError("Окно приложения ещё не создано")

            import webview
            dialog_type = (
                webview.FileDialog.OPEN
                if hasattr(webview, "FileDialog")
                else webview.OPEN_DIALOG
            )
            selected = self._window.create_file_dialog(
                dialog_type,
                allow_multiple=False,
                file_types=("CSV files (*.csv)", "All files (*.*)"),
            )
            if not selected:
                return {"ok": False, "cancelled": True}
            return self.load_csv(selected[0], name)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def export_csv(self, name, path):
        """Export a dataset to a CSV file."""
        try:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Не выбран набор данных")
            path = Path(path)
            with self._lock:
                frame = self.data_manager.get_data(name)
            save_csv_file(frame, path)
            return {
                "ok": True,
                "path": str(path),
                "message": f"Сохранено: {path.name}",
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def select_export_csv_file(self, name):
        """Show a native save dialog and export the selected dataset."""
        try:
            if self._window is None:
                raise RuntimeError("Окно приложения ещё не создано")

            import webview
            dialog_type = (
                webview.FileDialog.SAVE
                if hasattr(webview, "FileDialog")
                else webview.SAVE_DIALOG
            )
            selected = self._window.create_file_dialog(
                dialog_type,
                save_filename=f"{name}.csv",
                file_types=("CSV files (*.csv)",),
            )
            if not selected:
                return {"ok": False, "cancelled": True}
            return self.export_csv(name, selected[0])
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def preview_data(self, name, limit=100):
        """Return a JSON-safe preview of a dataset."""
        try:
            if not isinstance(limit, int) or isinstance(limit, bool):
                raise TypeError("limit must be an integer")
            if limit < 1 or limit > 500:
                raise ValueError("limit must be between 1 and 500")

            with self._lock:
                frame = self.data_manager.get_data(name)

            preview = frame.head(limit)
            rows = [
                [self._json_value(value) for value in row]
                for row in preview.itertuples(index=False, name=None)
            ]

            return {
                "ok": True,
                "name": name,
                "columns": [str(column) for column in frame.columns],
                "rows": rows,
                "total_rows": len(frame),
                "shown_rows": len(preview),
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def import_column_to_array(self, dataset_name, column, array_name):
        """Copy a numeric CSV column into a persistent formula array."""
        try:
            if not isinstance(array_name, str) or not array_name.strip():
                raise ValueError("Введите имя массива")
            array_name = array_name.strip()
            if not array_name.isidentifier():
                raise ValueError("Имя массива должно быть корректным идентификатором")
            if array_name in self.engine.get_variable_names() or array_name in self.engine.definitions or array_name in self.engine.functions:
                raise ValueError(f"Имя '{array_name}' уже используется")

            with self._lock:
                frame = self.data_manager.get_data(dataset_name)
                if column not in frame.columns:
                    raise KeyError(f"Не найден столбец: {column}")
                values = pd.to_numeric(frame[column], errors="coerce")
                if values.isna().any():
                    bad_rows = (np.flatnonzero(values.isna().to_numpy()) + 2).tolist()
                    raise ValueError(
                        f"Столбец '{column}' содержит пустые или нечисловые значения "
                        f"(строки CSV: {', '.join(map(str, bad_rows[:10]))})"
                    )
                array = values.to_numpy(dtype=float)
                if not np.all(np.isfinite(array)):
                    raise ValueError(f"Столбец '{column}' содержит NaN или бесконечность")
                if array_name in self.engine.external_variables:
                    raise ValueError(f"Массив '{array_name}' уже импортирован")
                self.engine.set_external_variable(array_name, array.copy())
                return {
                    "ok": True,
                    "state": self._build_state(),
                    "message": f"Столбец «{column}» импортирован в массив «{array_name}» ({len(array)} значений)",
                }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def remove_dataset(self, name):
        try:
            with self._lock:
                self.data_manager.remove_data(name)
                return {"ok": True, "state": self._build_state()}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def process_dataset(self, name, operation, column=None, options=None):
        """Apply a numerical operation to a dataset without modifying its source."""
        try:
            options = options or {}
            if not isinstance(options, dict):
                raise TypeError("options must be an object")
            x_column = options.get("x_column")
            window = options.get("window", 3)
            method = options.get("method", "moving_average")
            polyorder = options.get("polyorder", 2)
            minimum = options.get("minimum")
            maximum = options.get("maximum")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Не выбран набор данных")
            with self._lock:
                frame = self.data_manager.get_data(name)

            if operation == "smooth":
                if not column:
                    raise ValueError("Выберите столбец")
                result = smooth(frame, column, window=window, method=method, polyorder=polyorder)
                base_name = f"{name}_smooth"
                result_label = "Сглаживание"
            elif operation == "filter":
                if not column:
                    raise ValueError("Выберите столбец для фильтрации")
                result = filter_rows(
                    frame,
                    column,
                    minimum=minimum,
                    maximum=maximum,
                )
                base_name = f"{name}_filtered"
                result_label = "Фильтрация"
            elif operation == "derivative":
                if not column:
                    raise ValueError("Выберите столбец Y")
                if not x_column:
                    raise ValueError("Выберите столбец X")
                result = derivative(frame, column, x_column=x_column)
                base_name = f"{name}_derivative"
                result_label = "Производная"
            elif operation == "integrate":
                if not column:
                    raise ValueError("Выберите столбец")
                value = integrate(frame, column, x_column=x_column or None)
                x_label = x_column or "индекс строк"
                return {
                    "ok": True,
                    "result": self._format_value(value),
                    "message": f"Интеграл методом трапеций: ∫ {column} d({x_label})",
                }
            elif operation == "statistics":
                result = statistics(frame)
                return {"ok": True, "result": result.to_string(),
                        "message": "Статистика рассчитана"}
            else:
                raise ValueError("Неизвестная операция")

            with self._lock:
                output_name = base_name
                suffix = 2
                while output_name in self.data_manager:
                    output_name = f"{base_name}_{suffix}"
                    suffix += 1
                self.data_manager.add_data(output_name, result)

            return {"ok": True, "state": self._build_state(),
                    "dataset_name": output_name,
                    "message": f"{result_label}: создан набор «{output_name}»"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def render_plot_curves(self, curves, title=None):
        """Render multiple dataset/column combinations on one set of axes."""
        manager = None
        try:
            if not isinstance(curves, list) or not curves:
                raise ValueError("Добавьте хотя бы одну кривую")

            manager = PlotManager(
                title=title or "MathLab plot",
                xlabel="X",
                ylabel="Y",
            )

            labels_x = []
            labels_y = []

            for spec in curves:
                if not isinstance(spec, dict):
                    raise TypeError("Каждая кривая должна быть объектом")

                dataset_name = spec.get("dataset_name")
                x_column = spec.get("x_column")
                y_column = spec.get("y_column")
                label = spec.get("label")

                if not dataset_name or not x_column or not y_column:
                    raise ValueError(
                        "Для кривой нужны набор данных, X и Y"
                    )

                with self._lock:
                    frame = self.data_manager.get_data(dataset_name)

                if x_column not in frame.columns:
                    raise KeyError(f"Не найден столбец: {x_column}")
                if y_column not in frame.columns:
                    raise KeyError(f"Не найден столбец: {y_column}")

                manager.add_curve(
                    frame,
                    x_column,
                    y_column,
                    label=label or f"{dataset_name}: {y_column}",
                )
                labels_x.append(str(x_column))
                labels_y.append(str(y_column))

            manager.set_labels(
                xlabel=labels_x[0] if len(set(labels_x)) == 1 else "X",
                ylabel=labels_y[0] if len(set(labels_y)) == 1 else "Y",
            )

            buffer = BytesIO()
            manager.figure.savefig(
                buffer,
                format="png",
                dpi=140,
                bbox_inches="tight",
            )
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

            return {
                "ok": True,
                "image": f"data:image/png;base64,{encoded}",
                "curve_count": len(curves),
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            if manager is not None:
                manager.close()

    def render_plot_array_curves(self, curves, title=None):
        """Render curves directly from named engine array variables."""
        manager = None
        try:
            if not isinstance(curves, list) or not curves:
                raise ValueError("Добавьте хотя бы одну кривую")

            manager = PlotManager(
                title=title or "MathLab plot",
                xlabel="X",
                ylabel="Y",
            )
            labels_x = []
            labels_y = []

            with self._lock:
                variables = self.engine.variables.as_dict()
                for spec in curves:
                    if not isinstance(spec, dict):
                        raise TypeError("Каждая кривая должна быть объектом")
                    x_name = spec.get("x_name")
                    y_name = spec.get("y_name")
                    if not x_name or not y_name:
                        raise ValueError("Выберите массивы X и Y")
                    x = variables.get(x_name)
                    y = variables.get(y_name)
                    if not isinstance(x, np.ndarray) or not isinstance(y, np.ndarray):
                        raise ValueError(f"'{x_name}' и '{y_name}' должны быть массивами")
                    x = np.asarray(x, dtype=float).reshape(-1)
                    y = np.asarray(y, dtype=float).reshape(-1)
                    if len(x) != len(y):
                        raise ValueError(
                            f"Массивы '{x_name}' и '{y_name}' имеют разную длину: {len(x)} и {len(y)}"
                        )
                    if len(x) < 2:
                        raise ValueError("Для построения графика нужно минимум 2 точки")
                    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
                        raise ValueError(f"Массивы '{x_name}' и '{y_name}' содержат нечисловые значения")
                    frame = pd.DataFrame({"x": x, "y": y})
                    label = spec.get("label") or f"{y_name}({x_name})"
                    manager.add_curve(frame, "x", "y", label=label)
                    labels_x.append(x_name)
                    labels_y.append(y_name)

            manager.set_labels(
                xlabel=labels_x[0] if len(set(labels_x)) == 1 else "X",
                ylabel=labels_y[0] if len(set(labels_y)) == 1 else "Y",
            )
            buffer = BytesIO()
            manager.figure.savefig(buffer, format="png", dpi=140, bbox_inches="tight")
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            return {
                "ok": True,
                "image": f"data:image/png;base64,{encoded}",
                "curve_count": len(curves),
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            if manager is not None:
                manager.close()

    def render_plot(self, dataset_name, x_column, y_column, title=None):
        """Backward-compatible one-curve plotting method."""
        return self.render_plot_curves(
            [{
                "dataset_name": dataset_name,
                "x_column": x_column,
                "y_column": y_column,
                "label": dataset_name,
            }],
            title,
        )



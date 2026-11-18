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
        self.data_manager = DataManager()
        self.engine = MathEngine(file_provider=self._file_data)
        self._window = None
        self._lock = RLock()

    def _set_window(self, window):
        self._window = window

    def _file_data(self, file_numbers, column=None):
        """Return numeric data from loaded CSV files using their current UI order."""
        with self._lock:
            names = self.data_manager.list_datasets()
            frames = []
            for number in file_numbers:
                if number < 1 or number > len(names):
                    raise ValueError(
                        f"Файл №{number} не существует (загружено файлов: {len(names)})"
                    )
                frame = self.data_manager.get_data(names[number - 1])

                numeric_columns = [
                    str(name) for name in frame.columns
                    if self._is_numeric_column(frame[name])
                ]

                if column is None:
                    if len(file_numbers) != 1:
                        raise ValueError("Для нескольких файлов укажите столбец: file([1,2], \"column\")")
                    selected = numeric_columns
                    if not selected:
                        return np.empty((len(frame), 0), dtype=float)
                    data = frame[selected].apply(
                        lambda series: pd.to_numeric(
                            series.astype("string").str.strip().str.replace(",", ".", regex=False),
                            errors="coerce",
                        )
                    )
                    return data.to_numpy(dtype=float)

                if isinstance(column, str):
                    if column not in numeric_columns:
                        raise ValueError(
                            f"Числовой столбец «{column}» не найден в файле №{number}"
                        )
                    column_name = column
                else:
                    if column > len(numeric_columns):
                        raise ValueError(
                            f"В файле №{number} нет числового столбца №{column}"
                        )
                    column_name = numeric_columns[column - 1]

                values = pd.to_numeric(
                    frame[column_name].astype("string").str.strip().str.replace(",", ".", regex=False),
                    errors="coerce",
                ).to_numpy(dtype=float)
                frames.append(values)

            if len(frames) == 1:
                return frames[0]
            result = np.empty(len(frames), dtype=object)
            for index, values in enumerate(frames):
                result[index] = values
            return result

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
        """Render a SymPy expression or a numeric array as presentation MathML."""
        if isinstance(expression, np.ndarray):
            shape = " × ".join(str(size) for size in expression.shape)
            return (
                '<math xmlns="http://www.w3.org/1998/Math/MathML">'
                f'<mtext>Массив {shape}</mtext></math>'
            )
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
        variables = []
        for name in self.engine.get_variable_names():
            value = self.engine.get_variable(name)
            variable = {
                "name": name,
                "value": self._format_value(value),
                "imported": name in self.engine.external_variables,
            }
            if isinstance(value, np.ndarray):
                flat = np.asarray(value).reshape(-1)
                variable["array_preview"] = {
                    "values": [self._json_value(item) for item in flat[:12]],
                    "size": int(flat.size),
                    "shape": list(value.shape),
                }
            variables.append(variable)
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

    def load_csv_files(self, paths, name=None):
        """Load several CSV files, assigning unique dataset names automatically."""
        if not isinstance(paths, (list, tuple)) or not paths:
            return {"ok": False, "error": "Не выбраны CSV-файлы"}

        loaded = []
        errors = []
        for raw_path in paths:
            path = Path(raw_path)
            base_name = (name.strip() if name and len(paths) == 1 else path.stem) or "dataset"
            dataset_name = base_name
            suffix = 2
            while dataset_name in self.data_manager:
                dataset_name = base_name + "_" + str(suffix)
                suffix += 1
            response = self.load_csv(str(path), dataset_name)
            if response.get("ok"):
                loaded.append(path.name)
            else:
                errors.append(path.name + ": " + response.get("error", "ошибка загрузки"))

        if not loaded:
            return {"ok": False, "error": "\n".join(errors) or "Не удалось загрузить файлы"}
        with self._lock:
            state = self._build_state()
        message = "Загружено файлов: " + str(len(loaded))
        if errors:
            message += "; с ошибками: " + str(len(errors))
        return {"ok": True, "state": state, "message": message, "loaded": loaded, "errors": errors}

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
                allow_multiple=True,
                file_types=("CSV files (*.csv)", "All files (*.*)"),
            )
            if not selected:
                return {"ok": False, "cancelled": True}
            return self.load_csv_files(selected, name)
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
            selected_path = selected if isinstance(selected, (str, Path)) else selected[0]
            return self.export_csv(name, selected_path)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def export_table(self, name, path, file_format):
        """Export the selected dataset as an Excel workbook."""
        try:
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Не выбран набор данных")
            path = Path(path)
            file_format = str(file_format).lower()
            if file_format != "xlsx":
                raise ValueError("Таблицу можно экспортировать только в Excel; PNG и PDF предназначены для графиков")
            with self._lock:
                frame = self.data_manager.get_data(name)
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                frame.to_excel(writer, sheet_name="Данные", index=False)
                sheet = writer.sheets["Данные"]
                sheet.freeze_panes = "A2"
                sheet.auto_filter.ref = sheet.dimensions
                for column_cells in sheet.columns:
                    width = max(len(str(cell.value or "")) for cell in column_cells)
                    sheet.column_dimensions[column_cells[0].column_letter].width = min(width + 2, 40)
            return {"ok": True, "path": str(path), "message": f"Сохранено: {path.name}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def _fit_plot_curve(frame, x_column, y_column, options):
        """Return sampled approximation points and R-squared for a curve."""
        if options is None or not isinstance(options, dict):
            raise TypeError("Параметры аппроксимации должны быть объектом")
        model = options.get("model", "linear")
        degree = options.get("degree", 2)
        x = pd.to_numeric(frame[x_column], errors="coerce").to_numpy(dtype=float)
        y = pd.to_numeric(frame[y_column], errors="coerce").to_numpy(dtype=float)
        mask = np.isfinite(x) & np.isfinite(y)
        x, y = x[mask], y[mask]
        if len(x) < 2:
            raise ValueError("Для аппроксимации нужны минимум две числовые точки")
        if model in ("exponential", "power") and np.any(y <= 0):
            raise ValueError("Для экспоненциальной и степенной аппроксимации Y должен быть положительным")
        if model in ("logarithmic", "power") and np.any(x <= 0):
            raise ValueError("Для логарифмической и степенной аппроксимации X должен быть положительным")

        if model == "linear":
            coefficients = np.polyfit(x, y, 1)
            predict = lambda values: np.polyval(coefficients, values)
        elif model == "polynomial":
            if not isinstance(degree, int) or isinstance(degree, bool) or degree < 2 or degree >= len(x):
                raise ValueError("Степень полинома должна быть от 2 до числа точек минус 1")
            coefficients = np.polyfit(x, y, degree)
            predict = lambda values: np.polyval(coefficients, values)
        elif model == "exponential":
            coefficients = np.polyfit(x, np.log(y), 1)
            predict = lambda values: np.exp(np.polyval(coefficients, values))
        elif model == "logarithmic":
            coefficients = np.polyfit(np.log(x), y, 1)
            predict = lambda values: np.polyval(coefficients, np.log(values))
        elif model == "power":
            coefficients = np.polyfit(np.log(x), np.log(y), 1)
            predict = lambda values: np.exp(np.polyval(coefficients, np.log(values)))
        else:
            raise ValueError("Неизвестный тип аппроксимации")

        predicted = predict(x)
        residual = float(np.sum((y - predicted) ** 2))
        total = float(np.sum((y - np.mean(y)) ** 2))
        r_squared = 1.0 if total == 0 and residual == 0 else (0.0 if total == 0 else 1 - residual / total)
        x_fit = np.linspace(float(np.min(x)), float(np.max(x)), 300)
        y_fit = predict(x_fit)

        def number(value):
            return f"{float(value):.6g}"

        def signed_term(value, expression):
            sign = " + " if value >= 0 else " - "
            return sign + number(abs(value)) + expression

        if model in ("linear", "polynomial"):
            terms = []
            power = len(coefficients) - 1
            for index, coefficient in enumerate(coefficients):
                exponent = power - index
                if abs(coefficient) < 1e-12:
                    continue
                variable = "" if exponent == 0 else ("x" if exponent == 1 else f"x^{exponent}")
                if not terms:
                    terms.append(("-" if coefficient < 0 else "") + number(abs(coefficient)) + variable)
                else:
                    terms.append(signed_term(coefficient, variable))
            formula = "y = " + ("".join(terms) if terms else "0")
        elif model == "exponential":
            amplitude = float(np.exp(coefficients[1]))
            formula = f"y = {number(amplitude)}·e^({number(coefficients[0])}·x)"
        elif model == "logarithmic":
            formula = f"y = {number(coefficients[0])}·ln(x)" + signed_term(coefficients[1], "")
        else:
            amplitude = float(np.exp(coefficients[1]))
            formula = f"y = {number(amplitude)}·x^{number(coefficients[0])}"

        fit_frame = pd.DataFrame({x_column: x_fit, "__mathlab_fit__": y_fit})
        fit_frame.attrs["formula"] = formula
        return fit_frame, r_squared

    @staticmethod
    def _add_plot_curve(manager, frame, x_column, y_column, label, smoothing=None, approximation=None):
        """Add a curve, optionally smoothing Y without modifying source data."""
        plot_frame = frame
        plot_y = y_column
        if smoothing is not None and not isinstance(smoothing, dict):
            raise TypeError("Параметры сглаживания должны быть объектом")
        if smoothing and smoothing.get("enabled"):
            method = smoothing.get("method", "moving_average")
            window = smoothing.get("window", 5)
            polyorder = smoothing.get("polyorder", 2)
            plot_frame = smooth(
                frame, y_column, window=window, method=method,
                polyorder=polyorder, result_column="__mathlab_smoothed__",
            )
            plot_y = "__mathlab_smoothed__"
        manager.add_curve(plot_frame, x_column, plot_y, label=label)
        if approximation and approximation.get("enabled"):
            fit_frame, r_squared = MathLabBridge._fit_plot_curve(
                plot_frame, x_column, plot_y, approximation
            )
            manager.add_curve(
                fit_frame, x_column, "__mathlab_fit__",
                label=f"{label} — аппроксимация (R²={r_squared:.4f})",
            )
            return {
                "label": label,
                "formula": fit_frame.attrs["formula"],
                "r_squared": r_squared,
            }
        return None

    def select_export_plot_file(self, title, plot_curves, file_format, source="csv",
                                 legend_visible=True, legend_position="best", smoothing=None, approximation=None):
        """Export the current plot directly from its Matplotlib Figure."""
        manager = None
        try:
            formats = {
                "png": ("PNG image (*.png)", ".png"),
                "pdf": ("PDF document (*.pdf)", ".pdf"),
            }
            if file_format not in formats:
                raise ValueError("Неподдерживаемый формат экспорта графика")
            if not isinstance(plot_curves, list) or not plot_curves:
                raise ValueError("Сначала добавьте кривые на график")
            if source not in ("csv", "array"):
                raise ValueError("Неизвестный источник данных графика")

            manager = PlotManager(
                title=title or "MathLab plot",
                xlabel="X",
                ylabel="Y",
            )
            labels_x = []
            labels_y = []
            if source == "csv":
                for spec in plot_curves:
                    dataset_name = spec.get("dataset_name")
                    x_column = spec.get("x_column")
                    y_column = spec.get("y_column")
                    if not dataset_name or not x_column or not y_column:
                        raise ValueError("Для кривой нужны набор данных, X и Y")
                    with self._lock:
                        frame = self.data_manager.get_data(dataset_name)
                    if x_column not in frame.columns or y_column not in frame.columns:
                        raise KeyError(f"Не найдены столбцы {x_column}, {y_column}")
                    self._add_plot_curve(
                        manager, frame, x_column, y_column,
                        spec.get("label") or f"{dataset_name}: {y_column}", smoothing, approximation,
                    )
                    labels_x.append(str(x_column))
                    labels_y.append(str(y_column))
            else:
                with self._lock:
                    variables = self.engine.variables.as_dict()
                    for spec in plot_curves:
                        x_name, y_name = spec.get("x_name"), spec.get("y_name")
                        x, y = variables.get(x_name), variables.get(y_name)
                        if not isinstance(x, np.ndarray) or not isinstance(y, np.ndarray):
                            raise ValueError(f"'{x_name}' и '{y_name}' должны быть массивами")
                        x = np.asarray(x, dtype=float).reshape(-1)
                        y = np.asarray(y, dtype=float).reshape(-1)
                        if len(x) != len(y) or len(x) < 2:
                            raise ValueError("Массивы X и Y должны иметь одинаковую длину не менее 2")
                        if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
                            raise ValueError("Массивы содержат нечисловые значения")
                        self._add_plot_curve(
                            manager, pd.DataFrame({"x": x, "y": y}), "x", "y",
                            spec.get("label") or f"{y_name}({x_name})", smoothing, approximation,
                        )
                        labels_x.append(x_name)
                        labels_y.append(y_name)

            manager.set_labels(
                xlabel=labels_x[0] if len(set(labels_x)) == 1 else "X",
                ylabel=labels_y[0] if len(set(labels_y)) == 1 else "Y",
            )
            manager.set_legend(visible=legend_visible, position=legend_position)

            if self._window is None:
                raise RuntimeError("Окно приложения ещё не создано")
            import webview
            file_type, extension = formats[file_format]
            dialog_type = webview.FileDialog.SAVE if hasattr(webview, "FileDialog") else webview.SAVE_DIALOG
            selected = self._window.create_file_dialog(
                dialog_type,
                save_filename=f"{str(title or 'График').strip() or 'График'}{extension}",
                file_types=(file_type,),
            )
            if not selected:
                return {"ok": False, "cancelled": True}
            selected_path = selected if isinstance(selected, (str, Path)) else selected[0]
            path = Path(selected_path)
            if path.suffix.lower() != extension:
                path = path.with_suffix(extension)

            manager.figure.savefig(path, format=file_format, dpi=300, bbox_inches="tight")
            return {
                "ok": True,
                "path": str(path),
                "message": f"График сохранён: {path.name}",
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            if manager is not None:
                manager.close()

    def select_export_table_file(self, name, file_format):
        """Open a native save dialog for Excel export."""
        try:
            if self._window is None:
                raise RuntimeError("Окно приложения ещё не создано")
            formats = {
                "xlsx": ("Excel workbook (*.xlsx)", ".xlsx"),
            }
            if file_format not in formats:
                raise ValueError("Неподдерживаемый формат экспорта")
            import webview
            dialog_type = webview.FileDialog.SAVE if hasattr(webview, "FileDialog") else webview.SAVE_DIALOG
            file_type, extension = formats[file_format]
            selected = self._window.create_file_dialog(
                dialog_type,
                save_filename=f"{name}{extension}",
                file_types=(file_type,),
            )
            if not selected:
                return {"ok": False, "cancelled": True}
            # pywebview returns a string for SAVE dialogs, but a list for OPEN dialogs.
            # Indexing a string here would keep only the first character of the path.
            selected_path = selected if isinstance(selected, (str, Path)) else selected[0]
            path = Path(selected_path)
            if path.suffix.lower() != extension:
                path = path.with_suffix(extension)
            return self.export_table(name, path, file_format)
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

    def render_plot_curves(self, curves, title=None, legend_visible=True, legend_position="best", smoothing=None, approximation=None):
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
            approximations = []

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

                curve_label = label or f"{dataset_name}: {y_column}"
                fit_info = self._add_plot_curve(
                    manager, frame, x_column, y_column,
                    curve_label, smoothing, approximation,
                )
                if fit_info:
                    approximations.append(fit_info)
                labels_x.append(str(x_column))
                labels_y.append(str(y_column))

            manager.set_labels(
                xlabel=labels_x[0] if len(set(labels_x)) == 1 else "X",
                ylabel=labels_y[0] if len(set(labels_y)) == 1 else "Y",
            )
            manager.set_legend(visible=legend_visible, position=legend_position)

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
                "approximations": approximations,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            if manager is not None:
                manager.close()

    def render_plot_array_curves(self, curves, title=None, legend_visible=True, legend_position="best", smoothing=None, approximation=None):
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
            approximations = []

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
                    fit_info = self._add_plot_curve(manager, frame, "x", "y", label, smoothing, approximation)
                    if fit_info:
                        approximations.append(fit_info)
                    labels_x.append(x_name)
                    labels_y.append(y_name)

            manager.set_labels(
                xlabel=labels_x[0] if len(set(labels_x)) == 1 else "X",
                ylabel=labels_y[0] if len(set(labels_y)) == 1 else "Y",
            )
            manager.set_legend(visible=legend_visible, position=legend_position)
            buffer = BytesIO()
            manager.figure.savefig(buffer, format="png", dpi=140, bbox_inches="tight")
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
            return {
                "ok": True,
                "image": f"data:image/png;base64,{encoded}",
                "curve_count": len(curves),
                "approximations": approximations,
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



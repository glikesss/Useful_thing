import base64
from io import BytesIO
from pathlib import Path
from threading import RLock

import matplotlib
matplotlib.use("Agg", force=True)
import pandas as pd

from core import MathEngine
from data import DataManager, load_csv_file
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

    def _dataset_info(self, name):
        frame = self.data_manager.get_data(name, copy=False)
        return {
            "name": name,
            "rows": len(frame),
            "columns": [str(column) for column in frame.columns],
            "numeric_columns": [
                str(column)
                for column in frame.select_dtypes(include="number").columns
            ],
        }

    def _build_state(self):
        variables = [
            {
                "name": name,
                "value": self._format_value(self.engine.get_variable(name)),
            }
            for name in self.engine.get_variable_names()
        ]
        return {
            "lines": list(self.engine.lines),
            "variables": variables,
            "functions": list(self.engine.get_function_names()),
            "datasets": [
                self._dataset_info(name)
                for name in self.data_manager.list_datasets()
            ],
        }

    def get_state(self):
        with self._lock:
            return self._build_state()

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

    def remove_dataset(self, name):
        try:
            with self._lock:
                self.data_manager.remove_data(name)
                return {"ok": True, "state": self._build_state()}
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

import pytest
from io import BytesIO
import matplotlib
matplotlib.use("Agg", force=True)

import pandas as pd

from interface.bridge import MathLabBridge


def test_bridge_initial_state():
    bridge = MathLabBridge()

    state = bridge.get_state()

    assert state["lines"] == []
    assert state["variables"] == []
    assert state["functions"] == []
    assert state["datasets"] == []


def test_bridge_sets_formulas():
    bridge = MathLabBridge()

    response = bridge.set_lines([
        "a = 2",
        "f(x) = a*x",
    ])

    assert response["ok"] is True
    assert response["state"]["lines"] == ["a = 2", "f(x) = a*x"]
    assert "a" in [item["name"] for item in response["state"]["variables"]]
    assert "f" in response["state"]["functions"]


def test_bridge_previews_formula_without_applying_it():
    bridge = MathLabBridge()
    bridge.set_lines(["a = 2"])

    response = bridge.preview_formula("f(x) = a*x + 1")

    assert response["ok"] is True
    assert "<math" in response["mathml"]
    assert bridge.get_state()["lines"] == ["a = 2"]
    assert bridge.get_state()["functions"] == []


def test_bridge_formula_preview_reports_incomplete_expression():
    bridge = MathLabBridge()

    response = bridge.preview_formula("f(x) = (")

    assert response["ok"] is False
    assert response["error"]


def test_bridge_evaluates_expression():
    bridge = MathLabBridge()
    bridge.set_lines(["a = 2"])

    response = bridge.evaluate("a + 3")

    assert response["ok"] is True
    assert float(response["result"]) == 5.0


def test_bridge_calls_function():
    bridge = MathLabBridge()
    bridge.set_lines(["double(x) = 2*x"])

    response = bridge.call_function("double", [4])

    assert response["ok"] is True
    assert float(response["result"]) == 8.0


def test_bridge_reports_formula_error():
    bridge = MathLabBridge()

    response = bridge.set_lines(["broken = ("])

    assert response["ok"] is False
    assert response["error"]


def test_bridge_loads_csv(tmp_path):
    path = tmp_path / "measurement.csv"
    path.write_text("time,voltage\n0,1\n1,3\n2,5\n", encoding="utf-8")

    bridge = MathLabBridge()
    response = bridge.load_csv(path, "measurement")

    assert response["ok"] is True
    assert response["dataset"]["rows"] == 3
    assert response["dataset"]["numeric_columns"] == ["time", "voltage"]


def test_bridge_rejects_duplicate_dataset(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("x\n1\n", encoding="utf-8")

    bridge = MathLabBridge()
    bridge.load_csv(path, "data")

    response = bridge.load_csv(path, "data")

    assert response["ok"] is False
    assert "уже существует" in response["error"]



def test_bridge_exports_dataset_to_csv(tmp_path):
    source = tmp_path / "source.csv"
    output = tmp_path / "exported.csv"
    source.write_text("""time,value
0,1.5
1,2.5
""", encoding="utf-8")

    bridge = MathLabBridge()
    bridge.load_csv(source, "measurement")

    response = bridge.export_csv("measurement", output)

    assert response["ok"] is True
    assert output.is_file()
    exported = pd.read_csv(output)
    assert exported.to_dict(orient="list") == {
        "time": [0, 1],
        "value": [1.5, 2.5],
    }


def test_bridge_export_rejects_unknown_dataset(tmp_path):
    bridge = MathLabBridge()

    response = bridge.export_csv("missing", tmp_path / "missing.csv")

    assert response["ok"] is False
    assert not (tmp_path / "missing.csv").exists()


def test_bridge_removes_dataset(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("x\n1\n", encoding="utf-8")

    bridge = MathLabBridge()
    bridge.load_csv(path, "data")

    response = bridge.remove_dataset("data")

    assert response["ok"] is True
    assert response["state"]["datasets"] == []


def test_bridge_renders_plot(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("time,value\n0,0\n1,2\n2,4\n", encoding="utf-8")

    bridge = MathLabBridge()
    bridge.load_csv(path, "data")

    response = bridge.render_plot(
        "data",
        "time",
        "value",
        "Test plot",
    )

    assert response["ok"] is True
    assert response["image"].startswith("data:image/png;base64,")


def test_bridge_imports_csv_column_as_formula_array(tmp_path):
    path = tmp_path / "measurement.csv"
    path.write_text("time,voltage\n0,1.5\n1,2.5\n2,3.5\n", encoding="utf-8")
    bridge = MathLabBridge()
    bridge.load_csv(path, "measurement")

    response = bridge.import_column_to_array("measurement", "voltage", "u")

    assert response["ok"] is True
    assert "u" in response["state"]["arrays"]
    imported = next(item for item in response["state"]["variables"] if item["name"] == "u")
    assert imported["imported"] is True
    assert imported["array_preview"]["values"] == [1.5, 2.5, 3.5]
    assert bridge.engine.get_variable("u").tolist() == [1.5, 2.5, 3.5]
    assert bridge.evaluate("u*2")["ok"] is True
    assert bridge.data_manager.get_data("measurement")["voltage"].tolist() == [1.5, 2.5, 3.5]


def test_plot_curve_smoothing_does_not_modify_source_data():
    frame = pd.DataFrame({
        "time": [0, 1, 2, 3, 4],
        "value": [0.0, 10.0, 0.0, 10.0, 0.0],
    })

    class FakePlotManager:
        def add_curve(self, data, x_column, y_column, label=None):
            self.data = data.copy()
            self.x_column = x_column
            self.y_column = y_column
            self.label = label

    manager = FakePlotManager()
    MathLabBridge._add_plot_curve(
        manager,
        frame,
        "time",
        "value",
        "signal",
        {"enabled": True, "method": "moving_average", "window": 3},
    )

    assert manager.y_column == "__mathlab_smoothed__"
    assert manager.data[manager.y_column].tolist() == pytest.approx(
        [5.0, 10 / 3, 20 / 3, 10 / 3, 5.0]
    )
    assert frame["value"].tolist() == [0.0, 10.0, 0.0, 10.0, 0.0]


@pytest.mark.parametrize(
    ("model", "x", "y"),
    [
        ("linear", [1, 2, 3, 4], [3, 5, 7, 9]),
        ("polynomial", [-2, -1, 0, 1, 2], [4, 1, 0, 1, 4]),
        ("exponential", [0, 1, 2, 3], [2, 2 * np.e, 2 * np.e**2, 2 * np.e**3]),
        ("logarithmic", [1, np.e, np.e**2, np.e**3], [1, 3, 5, 7]),
        ("power", [1, 2, 3, 4], [1, 4, 9, 16]),
    ],
)
def test_plot_approximation_models(model, x, y):
    frame = pd.DataFrame({"x": x, "y": y})
    fit, r_squared = MathLabBridge._fit_plot_curve(
        frame, "x", "y", {"model": model, "degree": 2}
    )

    assert len(fit) == 300
    assert fit["x"].is_monotonic_increasing
    assert r_squared == pytest.approx(1.0, abs=1e-10)


def test_plot_approximation_rejects_nonpositive_logarithmic_inputs():
    frame = pd.DataFrame({"x": [0, 1, 2], "y": [1, 2, 3]})
    with pytest.raises(ValueError, match="X должен быть положительным"):
        MathLabBridge._fit_plot_curve(frame, "x", "y", {"model": "logarithmic"})


def test_bridge_rejects_import_of_non_numeric_csv_column(tmp_path):
    path = tmp_path / "measurement.csv"
    path.write_text("time,label\n0,a\n1,b\n", encoding="utf-8")
    bridge = MathLabBridge()
    bridge.load_csv(path, "measurement")

    response = bridge.import_column_to_array("measurement", "label", "labels")

    assert response["ok"] is False
    assert "нечисловые" in response["error"]


def test_imported_array_survives_formula_rebuild(tmp_path):
    path = tmp_path / "measurement.csv"
    path.write_text("time,voltage\n0,1\n1,2\n2,3\n", encoding="utf-8")
    bridge = MathLabBridge()
    bridge.load_csv(path, "measurement")
    assert bridge.import_column_to_array("measurement", "voltage", "u")["ok"] is True

    response = bridge.set_lines(["v = u * 2"])

    assert response["ok"] is True
    assert bridge.engine.get_variable("u").tolist() == [1.0, 2.0, 3.0]
    assert bridge.engine.get_variable("v").tolist() == [2.0, 4.0, 6.0]


def test_bridge_renders_plot_from_formula_arrays():
    bridge = MathLabBridge()
    applied = bridge.set_lines([
        "x = [0, 1, 2]",
        "y = [1, 4, 9]",
    ])
    assert applied["ok"] is True

    response = bridge.render_plot_array_curves([
        {"x_name": "x", "y_name": "y", "label": "y(x)"}
    ])

    assert response["ok"] is True
    assert response["curve_count"] == 1
    assert response["image"].startswith("data:image/png;base64,")


def test_bridge_rejects_array_plot_with_different_lengths():
    bridge = MathLabBridge()
    bridge.set_lines(["x = [0, 1, 2]", "y = [1, 4]"])

    response = bridge.render_plot_array_curves([
        {"x_name": "x", "y_name": "y"}
    ])

    assert response["ok"] is False
    assert "разную длину" in response["error"]


def test_bridge_rejects_non_array_plot_variables():
    bridge = MathLabBridge()
    bridge.set_lines(["x = 2", "y = [1, 2, 3]"])

    response = bridge.render_plot_array_curves([
        {"x_name": "x", "y_name": "y"}
    ])

    assert response["ok"] is False
    assert "должны быть массивами" in response["error"]


def test_bridge_previews_dataset(tmp_path):
    path = tmp_path / "preview.csv"
    path.write_text("time,value\n0,1\n1,2\n2,\n", encoding="utf-8")

    bridge = MathLabBridge()
    bridge.load_csv(path, "preview")

    response = bridge.preview_data("preview", 2)

    assert response["ok"] is True
    assert response["columns"] == ["time", "value"]
    assert response["rows"] == [[0, 1], [1, 2]]
    assert response["total_rows"] == 3
    assert response["shown_rows"] == 2


def test_bridge_preview_preserves_missing_values_as_none(tmp_path):
    path = tmp_path / "missing.csv"
    path.write_text("x,y\n1,\n", encoding="utf-8")

    bridge = MathLabBridge()
    bridge.load_csv(path, "missing")

    response = bridge.preview_data("missing")

    assert response["ok"] is True
    assert response["rows"] == [[1, None]]


def test_bridge_preview_rejects_invalid_limit():
    bridge = MathLabBridge()

    response = bridge.preview_data("missing", 0)

    assert response["ok"] is False


def test_bridge_renders_multiple_curves(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    first.write_text("time,a\n0,1\n1,2\n", encoding="utf-8")
    second.write_text("time,b\n0,3\n1,5\n", encoding="utf-8")

    bridge = MathLabBridge()
    bridge.load_csv(first, "first")
    bridge.load_csv(second, "second")

    response = bridge.render_plot_curves([
        {
            "dataset_name": "first",
            "x_column": "time",
            "y_column": "a",
            "label": "A",
        },
        {
            "dataset_name": "second",
            "x_column": "time",
            "y_column": "b",
            "label": "B",
        },
    ], "Comparison")

    assert response["ok"] is True
    assert response["curve_count"] == 2
    assert response["image"].startswith("data:image/png;base64,")



def test_bridge_processes_dataset_without_modifying_source(tmp_path):
    path = tmp_path / "signal.csv"
    path.write_text("time,value\n0,0\n1,2\n2,4\n", encoding="utf-8")
    bridge = MathLabBridge()
    bridge.load_csv(path, "signal")

    response = bridge.process_dataset(
        "signal", "derivative", "value", {"x_column": "time"}
    )

    assert response["ok"] is True
    assert response["dataset_name"] == "signal_derivative"
    assert "signal_derivative" in [item["name"] for item in response["state"]["datasets"]]
    assert bridge.data_manager.get_data("signal")["value"].tolist() == [0, 2, 4]
    assert bridge.data_manager.get_data("signal_derivative")["d_value_d_time"].tolist() == [2.0, 2.0, 2.0]


def test_bridge_filters_dataset_without_modifying_source(tmp_path):
    path = tmp_path / "signal.csv"
    path.write_text(
        "time,value\n0,10\n1,20\n2,30\n3,40\n",
        encoding="utf-8",
    )
    bridge = MathLabBridge()
    bridge.load_csv(path, "signal")

    response = bridge.process_dataset(
        "signal", "filter", "time", {"minimum": 1, "maximum": 2}
    )

    assert response["ok"] is True
    assert response["dataset_name"] == "signal_filtered"
    assert bridge.data_manager.get_data("signal")["time"].tolist() == [0, 1, 2, 3]
    filtered = bridge.data_manager.get_data("signal_filtered")
    assert filtered["time"].tolist() == [1, 2]
    assert filtered["value"].tolist() == [20, 30]


def test_bridge_filter_requires_at_least_one_bound(tmp_path):
    path = tmp_path / "signal.csv"
    path.write_text("time,value\n0,10\n1,20\n", encoding="utf-8")
    bridge = MathLabBridge()
    bridge.load_csv(path, "signal")

    response = bridge.process_dataset("signal", "filter", "time", {})

    assert response["ok"] is False
    assert "At least one bound" in response["error"]


def test_bridge_derivative_requires_x_column(tmp_path):
    path = tmp_path / "signal.csv"
    path.write_text("time,value\n0,0\n1,2\n2,6\n", encoding="utf-8")
    bridge = MathLabBridge()
    bridge.load_csv(path, "signal")

    response = bridge.process_dataset("signal", "derivative", "value")

    assert response["ok"] is False
    assert response["error"] == "Выберите столбец X"


def test_bridge_integrates_dataset(tmp_path):
    path = tmp_path / "signal.csv"
    path.write_text("time,value\n0,0\n1,2\n2,4\n", encoding="utf-8")
    bridge = MathLabBridge()
    bridge.load_csv(path, "signal")

    response = bridge.process_dataset(
        "signal", "integrate", "value", {"x_column": "time"}
    )

    assert response["ok"] is True
    assert float(response["result"]) == 4.0


def test_bridge_calculates_statistics(tmp_path):
    path = tmp_path / "signal.csv"
    path.write_text("time,value\n0,1\n1,3\n", encoding="utf-8")
    bridge = MathLabBridge()
    bridge.load_csv(path, "signal")

    response = bridge.process_dataset("signal", "statistics")

    assert response["ok"] is True
    assert "mean" in response["result"]
    assert "2.0" in response["result"]



def test_bridge_rejects_empty_curve_list():
    bridge = MathLabBridge()

    response = bridge.render_plot_curves([])

    assert response["ok"] is False



def test_bridge_applies_savgol_smoothing(tmp_path):
    path = tmp_path / "signal.csv"
    path.write_text(
        "time,value\n0,1\n1,4\n2,9\n3,16\n4,25\n5,36\n6,49\n",
        encoding="utf-8",
    )
    bridge = MathLabBridge()
    bridge.load_csv(path, "signal")

    response = bridge.process_dataset(
        "signal",
        "smooth",
        "value",
        {"window": 5, "method": "savgol", "polyorder": 2},
    )

    assert response["ok"] is True
    assert response["dataset_name"] == "signal_smooth"
    smoothed = bridge.data_manager.get_data("signal_smooth")["value_smoothed"]
    assert smoothed.tolist() == pytest.approx([1, 4, 9, 16, 25, 36, 49])


def test_bridge_includes_presentation_mathml_for_formulas():
    bridge = MathLabBridge()

    response = bridge.set_lines([
        "a = 1/2",
        "f(x) = sqrt(x^2 + 1)",
    ])

    assert response["ok"] is True
    formulas = response["state"]["formulas"]
    assert [item["name"] for item in formulas] == ["a", "f"]
    assert all(item["mathml"] for item in formulas)
    assert all("<math" in item["mathml"] for item in formulas)



def test_bridge_exports_full_table_to_excel(tmp_path):
    source = tmp_path / "source.csv"
    output = tmp_path / "table.xlsx"
    source.write_text("time,value\n0,1.5\n1,2.5\n", encoding="utf-8")
    bridge = MathLabBridge()
    bridge.load_csv(source, "measurement")

    response = bridge.export_table("measurement", output, "xlsx")

    assert response["ok"] is True
    exported = pd.read_excel(output)
    assert exported.to_dict(orient="list") == {"time": [0, 1], "value": [1.5, 2.5]}


@pytest.mark.parametrize("dialog_result_is_list", [False, True])
def test_table_export_save_dialog_handles_string_and_list_paths(
    tmp_path, monkeypatch, dialog_result_is_list
):
    import sys
    from types import SimpleNamespace

    source = tmp_path / "source.csv"
    output = tmp_path / "saved-table.xlsx"
    source.write_text("time,value\n0,1.5\n1,2.5\n", encoding="utf-8")

    bridge = MathLabBridge()
    bridge.load_csv(source, "measurement")

    selected = [str(output)] if dialog_result_is_list else str(output)

    class FakeWindow:
        def create_file_dialog(self, *args, **kwargs):
            return selected

    bridge._set_window(FakeWindow())
    monkeypatch.setitem(
        sys.modules,
        "webview",
        SimpleNamespace(FileDialog=SimpleNamespace(SAVE=1)),
    )

    response = bridge.select_export_table_file("measurement", "xlsx")

    assert response["ok"] is True, response
    assert output.is_file()
    exported = pd.read_excel(output)
    assert exported.to_dict(orient="list") == {
        "time": [0, 1],
        "value": [1.5, 2.5],
    }


def test_bridge_rejects_png_export_for_data_table(tmp_path):
    bridge = MathLabBridge()

    response = bridge.export_table("measurement", tmp_path / "table.png", "png")

    assert response["ok"] is False
    assert "только в Excel" in response["error"]


@pytest.mark.parametrize("file_format", ["png", "pdf"])
def test_bridge_exports_rendered_plot_with_matplotlib_savefig(tmp_path, monkeypatch, file_format):
    import sys
    from types import SimpleNamespace

    source = tmp_path / "source.csv"
    output = tmp_path / ("graph." + file_format)
    source.write_text("time,value\n0,0\n1,1\n2,4\n", encoding="utf-8")

    class FakeWindow:
        def create_file_dialog(self, *args, **kwargs):
            return str(output)

    bridge = MathLabBridge()
    bridge.load_csv(source, "measurement")
    bridge._set_window(FakeWindow())
    monkeypatch.setitem(
        sys.modules,
        "webview",
        SimpleNamespace(FileDialog=SimpleNamespace(SAVE=1)),
    )

    response = bridge.select_export_plot_file(
        "graph",
        [{"dataset_name": "measurement", "x_column": "time", "y_column": "value", "label": "y"}],
        file_format,
        "csv",
    )

    assert response["ok"] is True, response
    assert output.is_file()
    assert output.stat().st_size > 0
    assert output.read_bytes().startswith(b"%PDF" if file_format == "pdf" else b"\x89PNG")

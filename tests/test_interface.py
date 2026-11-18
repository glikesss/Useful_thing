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
    path.write_text("time,value\\n0,0\\n1,2\\n2,4\\n", encoding="utf-8")
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


def test_bridge_integrates_dataset(tmp_path):
    path = tmp_path / "signal.csv"
    path.write_text("time,value\\n0,0\\n1,2\\n2,4\\n", encoding="utf-8")
    bridge = MathLabBridge()
    bridge.load_csv(path, "signal")

    response = bridge.process_dataset(
        "signal", "integrate", "value", {"x_column": "time"}
    )

    assert response["ok"] is True
    assert float(response["result"]) == 4.0


def test_bridge_calculates_statistics(tmp_path):
    path = tmp_path / "signal.csv"
    path.write_text("time,value\\n0,1\\n1,3\\n", encoding="utf-8")
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

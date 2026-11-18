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


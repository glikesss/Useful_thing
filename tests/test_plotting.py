import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import pytest

from data import Experiment
from plotting import Curve, PlotManager


def test_curve_creation():
    data = pd.DataFrame({"time": [0, 1, 2], "value": [2, 4, 6]})

    curve = Curve(data, "time", "value", label="Measurement")

    x, y = curve.get_values()

    assert x.tolist() == [0, 1, 2]
    assert y.tolist() == [2, 4, 6]
    assert curve.label == "Measurement"


def test_curve_parses_localized_infinity_values():
    data = pd.DataFrame({
        "x": ["-бесконечность", "0", "бесконечность"],
        "y": [1, 2, 3],
    })

    x, y = Curve(data, "x", "y").get_values()

    assert x[0] == float("-inf")
    assert x[1] == 0
    assert x[2] == float("inf")
    assert y.tolist() == [1, 2, 3]


def test_curve_copies_source_data():
    data = pd.DataFrame({"x": [1], "y": [2]})
    curve = Curve(data, "x", "y")

    data.loc[0, "y"] = 100

    assert curve.get_values()[1].tolist() == [2]


def test_curve_rejects_missing_column():
    data = pd.DataFrame({"x": [1]})

    with pytest.raises(KeyError):
        Curve(data, "x", "missing")


def test_curve_rejects_non_dataframe():
    with pytest.raises(TypeError):
        Curve([1, 2], "x", "y")


def test_plot_manager_add_curve():
    manager = PlotManager(
        title="Experiment",
        xlabel="Time",
        ylabel="Voltage",
    )
    data = pd.DataFrame({"time": [0, 1], "voltage": [1, 3]})

    line = manager.add_curve(
        data,
        "time",
        "voltage",
        label="Sensor",
    )

    assert len(manager.curves) == 1
    assert line.get_label() == "Sensor"
    assert line.get_xdata().tolist() == [0, 1]
    assert line.get_ydata().tolist() == [1, 3]

    manager.close()


def test_plot_manager_supports_curve_object():
    manager = PlotManager()
    curve = Curve(
        pd.DataFrame({"x": [0, 1], "y": [2, 3]}),
        "x",
        "y",
        style={"color": "red"},
    )

    line = manager.add_curve(curve)

    assert line.get_color() == "red"
    manager.close()


def test_plot_manager_add_experiment():
    experiment = Experiment(
        "Trial A",
        pd.DataFrame({"time": [0, 1], "value": [5, 10]}),
    )
    manager = PlotManager()

    line = manager.add_experiment(experiment, "time", "value")

    assert line.get_label() == "Trial A"
    assert len(manager.curves) == 1

    manager.close()


def test_plot_manager_remove_curve():
    manager = PlotManager()
    data = pd.DataFrame({"x": [0, 1], "y": [1, 2]})

    manager.add_curve(data, "x", "y", label="A")
    manager.add_curve(data, "x", "y", label="B")

    removed = manager.remove_curve(0)

    assert removed.label == "A"
    assert len(manager.curves) == 1
    assert manager.curves[0].label == "B"

    manager.close()


def test_plot_manager_remove_invalid_index():
    manager = PlotManager()

    with pytest.raises(IndexError):
        manager.remove_curve(0)

    manager.close()


def test_plot_manager_clear():
    manager = PlotManager(title="Test", xlabel="Time")
    data = pd.DataFrame({"x": [0, 1], "y": [1, 2]})

    manager.add_curve(data, "x", "y", label="A")
    manager.clear()

    assert len(manager.curves) == 0
    assert len(manager.axes.lines) == 0
    assert manager.axes.get_title() == "Test"
    assert manager.axes.get_xlabel() == "Time"

    manager.close()


def test_plot_manager_updates_labels():
    manager = PlotManager()
    manager.set_title("New title")
    manager.set_labels(xlabel="Time", ylabel="Distance")

    assert manager.axes.get_title() == "New title"
    assert manager.axes.get_xlabel() == "Time"
    assert manager.axes.get_ylabel() == "Distance"

    manager.close()


def test_plot_manager_saves_figure(tmp_path):
    manager = PlotManager()
    data = pd.DataFrame({"x": [0, 1], "y": [1, 2]})
    manager.add_curve(data, "x", "y")

    path = tmp_path / "plot.png"
    result = manager.save(path)

    assert result == path
    assert path.exists()
    assert path.stat().st_size > 0

    manager.close()


def test_plotting_public_api():
    from plotting import __all__

    assert set(__all__) == {"Curve", "PlotManager"}
    assert callable(PlotManager)
    assert callable(Curve)


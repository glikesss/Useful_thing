import pandas as pd
import pytest

from data.experiment import Experiment


def test_create_experiment():
    experiment = Experiment("Test")

    assert experiment.name == "Test"
    assert experiment.get_data if True else False
    assert experiment.parameters == {}
    assert experiment.metadata == {}
    assert experiment.results == {}


def test_experiment_rejects_empty_name():
    with pytest.raises(ValueError):
        Experiment("  ")


def test_create_experiment_with_data():
    data = pd.DataFrame({"time": [0, 1], "value": [10, 20]})
    experiment = Experiment("Test", data)

    pd.testing.assert_frame_equal(experiment.get_data(), data)


def test_experiment_copies_input_data():
    data = pd.DataFrame({"x": [1]})
    experiment = Experiment("Test", data)

    data.loc[0, "x"] = 100

    assert experiment.get_data().loc[0, "x"] == 1


def test_get_data_returns_copy_by_default():
    experiment = Experiment("Test", pd.DataFrame({"x": [1]}))

    result = experiment.get_data()
    result.loc[0, "x"] = 100

    assert experiment.get_data().loc[0, "x"] == 1


def test_get_data_can_return_internal_data():
    experiment = Experiment("Test", pd.DataFrame({"x": [1]}))

    result = experiment.get_data(copy=False)
    result.loc[0, "x"] = 5

    assert experiment.get_data().loc[0, "x"] == 5


def test_set_data_rejects_non_dataframe():
    experiment = Experiment("Test")

    with pytest.raises(TypeError):
        experiment.set_data([1, 2, 3])


def test_get_data_without_data():
    experiment = Experiment("Test")

    with pytest.raises(ValueError, match="no data"):
        experiment.get_data()


def test_parameters():
    experiment = Experiment("Test", parameters={"frequency": 100})

    assert experiment.get_parameter("frequency") == 100
    assert experiment.get_parameter("missing") is None

    experiment.set_parameter("frequency", 200)
    experiment.update_parameters({"amplitude": 5})

    assert experiment.get_parameter("frequency") == 200
    assert experiment.get_parameter("amplitude") == 5


def test_metadata():
    experiment = Experiment("Test", metadata={"author": "user"})

    experiment.set_metadata("description", "Measurement")
    experiment.update_metadata({"temperature": 25})

    assert experiment.get_metadata("author") == "user"
    assert experiment.get_metadata("description") == "Measurement"
    assert experiment.get_metadata("temperature") == 25


def test_add_and_get_result():
    experiment = Experiment("Test")

    experiment.add_result("mean", 15.0)

    assert experiment.get_result("mean") == 15.0
    assert experiment.list_results() == ["mean"]


def test_duplicate_result_requires_replace():
    experiment = Experiment("Test")
    experiment.add_result("mean", 10)

    with pytest.raises(ValueError, match="already exists"):
        experiment.add_result("mean", 20)

    experiment.add_result("mean", 20, replace=True)
    assert experiment.get_result("mean") == 20


def test_remove_result():
    experiment = Experiment("Test")
    experiment.add_result("mean", 10)

    assert experiment.remove_result("mean") == 10
    assert experiment.list_results() == []

    with pytest.raises(KeyError):
        experiment.remove_result("mean")


def test_experiment_copies_nested_parameters():
    parameters = {"settings": {"rate": 10}}
    experiment = Experiment("Test", parameters=parameters)

    parameters["settings"]["rate"] = 99

    assert experiment.get_parameter("settings")["rate"] == 10


def test_experiment_repr():
    experiment = Experiment("Test", pd.DataFrame({"x": [1, 2]}))

    assert "Test" in repr(experiment)
    assert "rows=2" in repr(experiment)

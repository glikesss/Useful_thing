import pandas as pd

import data
from data import (
    DataManager,
    Experiment,
    derivative,
    drop_missing,
    filter_rows,
    integrate,
    load_csv_file,
    load_csv_files,
    merge_csv_files,
    select_columns,
    smooth,
    statistics,
)


def test_public_api_exports_all_components():
    expected = {
        "DataManager",
        "Experiment",
        "load_csv_file",
        "load_csv_files",
        "merge_csv_files",
        "select_columns",
        "drop_missing",
        "filter_rows",
        "smooth",
        "derivative",
        "integrate",
        "statistics",
    }

    assert expected.issubset(set(data.__all__))

    for name in expected:
        assert hasattr(data, name)


def test_public_api_classes():
    assert DataManager.__name__ == "DataManager"
    assert Experiment.__name__ == "Experiment"


def test_public_api_processing_functions():
    functions = [
        derivative,
        drop_missing,
        filter_rows,
        integrate,
        load_csv_file,
        load_csv_files,
        merge_csv_files,
        select_columns,
        smooth,
        statistics,
    ]

    assert all(callable(function) for function in functions)


def test_complete_data_workflow(tmp_path):
    source = tmp_path / "measurement.csv"
    source.write_text(
        "time,signal\n0,0\n1,2\n2,4\n",
        encoding="utf-8",
    )

    manager = DataManager()
    manager.load_csv("measurement", source)

    experiment = Experiment(
        "test_experiment",
        manager.get_data("measurement"),
        parameters={"sensor": "test"},
        metadata={"source": "measurement.csv"},
    )

    processed = smooth(
        experiment.get_data(),
        "signal",
        window=3,
    )

    area = integrate(
        processed,
        "signal_smoothed",
        x_column="time",
    )

    experiment.add_result("processed_data", processed)
    experiment.add_result("integral", area)

    assert experiment.name == "test_experiment"
    assert experiment.get_parameter("sensor") == "test"
    assert experiment.get_result("integral") == 4.0
    assert len(experiment.get_result("processed_data")) == 3


def test_public_api_preserves_dataframe():
    source = pd.DataFrame({"x": [1, 2, 3]})

    manager = DataManager()
    manager.add_data("test", source)

    experiment = Experiment("test", manager.get_data("test"))

    pd.testing.assert_frame_equal(
        experiment.get_data(),
        source,
    )

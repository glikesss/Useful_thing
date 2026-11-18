import pandas as pd
import pytest

from data.data_manager import DataManager


def test_add_and_get_data():
    manager = DataManager()
    source = pd.DataFrame({"x": [1, 2]})

    manager.add_data("experiment", source)
    result = manager.get_data("experiment")

    pd.testing.assert_frame_equal(result, source)


def test_add_data_stores_independent_copy():
    manager = DataManager()
    source = pd.DataFrame({"x": [1]})

    manager.add_data("data", source)
    source.loc[0, "x"] = 99

    assert manager.get_data("data").loc[0, "x"] == 1


def test_add_data_rejects_duplicate_name():
    manager = DataManager()
    manager.add_data("data", pd.DataFrame({"x": [1]}))

    with pytest.raises(ValueError, match="already exists"):
        manager.add_data("data", pd.DataFrame({"x": [2]}))


def test_add_data_can_replace():
    manager = DataManager()
    manager.add_data("data", pd.DataFrame({"x": [1]}))
    manager.add_data("data", pd.DataFrame({"x": [2]}), replace=True)

    assert manager.get_data("data").loc[0, "x"] == 2


def test_add_data_rejects_non_dataframe():
    manager = DataManager()

    with pytest.raises(TypeError):
        manager.add_data("data", [1, 2, 3])


def test_load_csv(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("x,y\n1,2\n", encoding="utf-8")

    manager = DataManager()
    result = manager.load_csv("experiment", path)

    assert result.shape == (1, 2)
    assert "experiment" in manager


def test_list_and_remove_datasets():
    manager = DataManager()
    manager.add_data("first", pd.DataFrame({"x": [1]}))
    manager.add_data("second", pd.DataFrame({"x": [2]}))

    assert manager.list_datasets() == ["first", "second"]

    manager.remove_data("first")

    assert manager.list_datasets() == ["second"]
    assert len(manager) == 1


def test_get_unknown_dataset():
    manager = DataManager()

    with pytest.raises(KeyError):
        manager.get_data("missing")


def test_merge_data_aligns_columns():
    manager = DataManager()
    manager.add_data("first", pd.DataFrame({"x": [1, 2]}))
    manager.add_data("second", pd.DataFrame({"y": [3]}))

    result = manager.merge_data(["first", "second"], "merged")

    assert list(result.columns) == ["x", "y"]
    assert len(result) == 3
    assert pd.isna(result.loc[0, "y"])
    assert pd.isna(result.loc[2, "x"])
    assert result.loc[2, "y"] == 3


def test_merge_data_rejects_empty_names():
    manager = DataManager()

    with pytest.raises(ValueError):
        manager.merge_data([], "merged")


def test_merge_data_rejects_missing_dataset():
    manager = DataManager()

    with pytest.raises(KeyError):
        manager.merge_data(["missing"], "merged")


def test_export_csv(tmp_path):
    manager = DataManager()
    manager.add_data("data", pd.DataFrame({"x": [1, 2]}))

    path = tmp_path / "export.csv"
    manager.export_csv("data", path)

    result = pd.read_csv(path)
    assert result["x"].tolist() == [1, 2]


def test_invalid_dataset_name():
    manager = DataManager()

    with pytest.raises(ValueError):
        manager.add_data("  ", pd.DataFrame({"x": [1]}))

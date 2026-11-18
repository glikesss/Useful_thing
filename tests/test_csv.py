import pandas as pd
import pytest

from data.csv_loader import (
    load_csv_file,
    load_csv_files,
    merge_csv_files,
)


def test_load_csv_file(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")

    result = load_csv_file(path)

    assert list(result.columns) == ["x", "y"]
    assert result.shape == (2, 2)
    assert result.iloc[0].tolist() == [1, 2]


def test_load_csv_files_aligns_columns_by_name(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"

    first.write_text("time,value\n0,10\n1,20\n", encoding="utf-8")
    second.write_text("value,temperature\n30,100\n40,200\n", encoding="utf-8")

    result = load_csv_files([first, second])

    assert list(result.columns) == ["time", "value", "temperature"]
    assert len(result) == 4

    assert result.loc[0, "time"] == 0
    assert result.loc[0, "value"] == 10
    assert pd.isna(result.loc[0, "temperature"])

    assert pd.isna(result.loc[2, "time"])
    assert result.loc[2, "value"] == 30
    assert result.loc[2, "temperature"] == 100


def test_load_csv_files_resets_index(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"

    first.write_text("x\n1\n2\n", encoding="utf-8")
    second.write_text("x\n3\n", encoding="utf-8")

    result = load_csv_files([first, second])

    assert result.index.tolist() == [0, 1, 2]


def test_load_csv_files_accepts_single_path(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("x\n1\n", encoding="utf-8")

    result = load_csv_files(path)

    assert result["x"].tolist() == [1]


def test_load_csv_files_supports_custom_separator(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("x;y\n1;2\n", encoding="utf-8")

    result = load_csv_file(path, sep=";")

    assert result.iloc[0].tolist() == [1, 2]


def test_load_csv_files_rejects_empty_list():
    with pytest.raises(ValueError, match="At least one"):
        load_csv_files([])


def test_load_csv_file_missing_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_csv_file(tmp_path / "missing.csv")


def test_load_csv_file_empty_file(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="empty"):
        load_csv_file(path)


def test_merge_csv_files_writes_output(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    output = tmp_path / "merged.csv"

    first.write_text("x\n1\n", encoding="utf-8")
    second.write_text("x\n2\n", encoding="utf-8")

    result = merge_csv_files([first, second], output)

    assert result["x"].tolist() == [1, 2]

    saved = pd.read_csv(output)
    assert saved["x"].tolist() == [1, 2]

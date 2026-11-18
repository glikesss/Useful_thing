import pandas as pd

from data.csv_loader import load_csv_file


def test_csv_decimal_comma_and_units(tmp_path):
    path = tmp_path / "comma.csv"
    path.write_text(
        "time;voltage;label\n"
        "(ms);(V);(name)\n"
        "0,5;1,25;first\n"
        "1,0;2,50;second\n",
        encoding="utf-8",
    )

    frame = load_csv_file(path)

    assert frame["time (ms)"].tolist() == [0.5, 1.0]
    assert frame["voltage (V)"].tolist() == [1.25, 2.5]
    assert frame["label (name)"].tolist() == ["first", "second"]


def test_csv_decimal_point_and_units(tmp_path):
    path = tmp_path / "dot.csv"
    path.write_text(
        "time;voltage\n"
        "(s);(V)\n"
        "0.5;1.25\n"
        "1.0;2.50\n",
        encoding="utf-8",
    )

    frame = load_csv_file(path)

    assert frame["time (s)"].tolist() == [0.5, 1.0]
    assert frame["voltage (V)"].tolist() == [1.25, 2.5]
    assert pd.api.types.is_numeric_dtype(frame["time (s)"])



def test_csv_empty_numeric_cells_become_nan(tmp_path):
    path = tmp_path / "empty_cells.csv"
    path.write_text(
        "time;voltage\\n"
        "0;1.5\\n"
        "1;\\n"
        "2;3.5\\n",
        encoding="utf-8",
    )

    frame = load_csv_file(path)

    assert frame["time"].tolist() == [0, 1, 2]
    assert frame["voltage"].iloc[0] == 1.5
    assert pd.isna(frame["voltage"].iloc[1])
    assert frame["voltage"].iloc[2] == 3.5
    assert pd.api.types.is_numeric_dtype(frame["voltage"])


def test_csv_strips_extra_spaces_from_values(tmp_path):
    path = tmp_path / "spaces.csv"
    path.write_text(
        "time;label\\n"
        " 0 ; first value \\n"
        " 1 ; second value \\n",
        encoding="utf-8",
    )

    frame = load_csv_file(path)

    assert frame["time"].tolist() == [0, 1]
    assert frame["label"].tolist() == ["first value", "second value"]


def test_csv_preserves_mixed_numeric_and_text_column(tmp_path):
    path = tmp_path / "mixed.csv"
    path.write_text(
        "measurement\\n"
        "1.5\\n"
        " sensor offline \\n"
        "2.5\\n",
        encoding="utf-8",
    )

    frame = load_csv_file(path)

    assert frame["measurement"].tolist() == ["1.5", "sensor offline", "2.5"]
    assert not pd.api.types.is_numeric_dtype(frame["measurement"])

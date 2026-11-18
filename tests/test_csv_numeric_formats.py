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

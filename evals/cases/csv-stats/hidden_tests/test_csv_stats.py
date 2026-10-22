import json

import pytest
from csv_stats import column_stats, format_report


def _csv(tmp_path, text):
    path = tmp_path / "data.csv"
    path.write_text(text)
    return str(path)


def test_numeric_columns_only(tmp_path):
    path = _csv(tmp_path, 'name,age,score\nada,36,9.5\nbob,,7\n"c, d",40,8\n')
    assert column_stats(path) == {
        "age": {"count": 2, "min": 36.0, "max": 40.0, "mean": 38.0},
        "score": {"count": 3, "min": 7.0, "max": 9.5, "mean": 8.17},
    }


def test_blank_and_whitespace_values_are_ignored(tmp_path):
    path = _csv(tmp_path, "a,b\n 1 ,\n2,  \n")
    assert column_stats(path) == {"a": {"count": 2, "min": 1.0, "max": 2.0, "mean": 1.5}}


def test_missing_file(tmp_path):
    missing = str(tmp_path / "nope.csv")
    with pytest.raises(FileNotFoundError, match=f"^no such file: {missing}$"):
        column_stats(missing)


@pytest.mark.parametrize("text", ["", "a,b\n"])
def test_no_data_rows(tmp_path, text):
    with pytest.raises(ValueError, match="^no data rows$"):
        column_stats(_csv(tmp_path, text))


def test_ragged_row(tmp_path):
    with pytest.raises(ValueError, match="^row 2: expected 2 fields, got 3$"):
        column_stats(_csv(tmp_path, "a,b\n1,2\n3,4,5\n"))


def test_format_report():
    stats = {"b": {"count": 1, "min": 1.0, "max": 1.0, "mean": 1.0}, "a": {}}
    report = format_report(stats)
    assert report.endswith("}\n")
    assert report == json.dumps(stats, indent=2, sort_keys=True) + "\n"

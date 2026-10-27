import csv, io, json
import pytest
import json2csv


def run(data, **kw):
    buf = io.StringIO()
    n = json2csv.convert(data, buf, **kw)
    return n, list(csv.reader(io.StringIO(buf.getvalue())))


def test_missing_keys_are_empty_strings():
    n, rows = run([{"a": 1, "b": 2}, {"b": 3, "c": "x"}])
    assert n == 2
    assert rows == [["a", "b", "c"], ["1", "2", ""], ["", "3", "x"]]


def test_special_characters_are_quoted():
    _, rows = run([{"t": 'he said "hi", then\nleft', "u": "Grüße ✓"}])
    assert rows[1] == ['he said "hi", then\nleft', "Grüße ✓"]


def test_none_bool_nested():
    _, rows = run([{"a": None, "b": True, "c": {"x": 1}}])
    assert rows[1] == ["", "true", '{"x":1}']


def test_custom_columns_and_delimiter():
    buf = io.StringIO()
    json2csv.convert([{"a": 1, "b": 2}], buf, delimiter=";", columns=["b", "a"])
    assert buf.getvalue() == "b;a\n2;1\n"


@pytest.mark.parametrize("bad", [{"a": 1}, [1, 2], "x"])
def test_rejects_non_array_of_objects(bad):
    with pytest.raises(json2csv.ConversionError):
        json2csv.convert(bad, io.StringIO())


def test_cli_roundtrip(tmp_path):
    src = tmp_path / "in.json"
    src.write_text(json.dumps([{"id": 1, "name": "Ana"}, {"id": 2}]), encoding="utf-8")
    out = tmp_path / "out.csv"
    assert json2csv.main([str(src), "-o", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == "id,name\n1,Ana\n2,\n"


def test_cli_errors(tmp_path):
    assert json2csv.main([str(tmp_path / "missing.json")]) == 2
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert json2csv.main([str(bad)]) == 3

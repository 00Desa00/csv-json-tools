import json
import pytest
import csv2json


@pytest.mark.parametrize("delim", [",", ";", "\t", "|"])
def test_autodetect_delimiters(delim):
    text = delim.join(["id", "name"]) + "\n" + delim.join(["1", "Ana"]) + "\n"
    header, rows = csv2json.parse(text)
    assert header == ["id", "name"] and rows == [["1", "Ana"]]


def test_quotes_newlines_unicode_bom():
    text = '\ufeffname,quote\n"Müller, A.","line1\nline2 ""ok"""\n'
    header, rows = csv2json.parse(text)
    assert header == ["name", "quote"]
    assert rows == [["Müller, A.", 'line1\nline2 "ok"']]
    out = json.loads(csv2json.render(header, rows))
    assert out == [{"name": "Müller, A.", "quote": 'line1\nline2 "ok"'}]


def test_type_inference():
    _, rows = csv2json.parse("a,b,c,d,e\n1,2.5,true,,007\n", infer_types=True)
    assert rows == [[1, 2.5, True, None, "007"]]


def test_ragged_rows_padded_or_strict():
    header, rows = csv2json.parse("a,b\n1\n2,3,4\n")
    assert header == ["a", "b", "col3"]
    assert rows == [["1", "", ""], ["2", "3", "4"]]
    with pytest.raises(csv2json.CSVError):
        csv2json.parse("a,b\n1\n", strict=True)


def test_duplicate_and_blank_headers():
    header, _ = csv2json.parse("a,a,\n1,2,3\n")
    assert header == ["a", "a_2", "col3"]


def test_formats():
    h, r = ["a"], [["1"], ["2"]]
    assert csv2json.render(h, r, "jsonl") == '{"a": "1"}\n{"a": "2"}\n'
    assert json.loads(csv2json.render(h, r, "table")) == {"columns": ["a"], "rows": [["1"], ["2"]]}
    assert csv2json.render(h, r, indent=None) == '[{"a":"1"},{"a":"2"}]\n'


def test_empty_input_errors():
    for t in ["", "   \n"]:
        with pytest.raises(csv2json.CSVError):
            csv2json.parse(t)


def test_cli(tmp_path):
    src = tmp_path / "in.csv"
    src.write_text("id;city\n1;Köln\n", encoding="utf-8")
    out = tmp_path / "out.json"
    assert csv2json.main([str(src), "-o", str(out), "--infer-types"]) == 0
    assert json.loads(out.read_text(encoding="utf-8")) == [{"id": 1, "city": "Köln"}]
    assert csv2json.main([str(tmp_path / "nope.csv")]) == 2
    latin = tmp_path / "latin.csv"
    latin.write_bytes("a\n\xe9\n".encode("latin-1"))
    assert csv2json.main([str(latin)]) == 3
    assert csv2json.main([str(latin), "--encoding", "latin-1"]) == 0

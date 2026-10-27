# csv-json-tools

Two small, dependency-free Python 3.10+ command-line tools:

- `json2csv.py`: JSON array of flat objects to CSV. Missing keys become empty strings.
- `csv2json.py`: CSV of any structure to JSON (delimiter auto-detection, type inference, 3 output formats).

Only the standard library is used. Tests use `pytest`.

## json2csv

```bash
python json2csv.py input.json -o output.csv
python json2csv.py input.json -d ";" -c id,name,email   # delimiter + fixed column order
cat input.json | python json2csv.py - > output.csv
```

- Columns are the union of all keys, in order of first appearance.
- Missing keys and `null` become `""`. Booleans become `true`/`false`.
- Commas, quotes and newlines inside values are quoted per RFC 4180.
- Nested values are written as compact JSON instead of failing.
- Exit codes: 0 ok, 2 file not found, 3 invalid JSON, 4 not an array of objects.

## csv2json

```bash
python csv2json.py input.csv -o output.json            # array of objects, indent 2
python csv2json.py input.csv --infer-types --indent 0  # numbers/bools/null, compact
python csv2json.py input.tsv -d '\t' -f jsonl           # tab-separated in, JSON Lines out
python csv2json.py input.csv -f table                  # {"columns": [...], "rows": [[...]]}
python csv2json.py legacy.csv --encoding latin-1 --strict
```

| Option | Meaning |
|---|---|
| `-d, --delimiter` | field delimiter; auto-detects `, ; TAB \|` if omitted |
| `-f, --format` | `records` (default), `jsonl`, `table` |
| `--indent N` | pretty-print with N spaces; `0` = compact |
| `--infer-types` | `1` to int, `2.5` to float, `true/false` to bool, empty to `null` (leading-zero values like `007` stay strings) |
| `--no-header` | treat first row as data; columns named `col1..N` |
| `--strict` | error on rows with the wrong number of fields (default: pad/extend) |
| `--sort-keys`, `--ascii` | sorted keys / escape non-ASCII |
| `--encoding` | input encoding (default `utf-8-sig`, which strips a BOM) |

Handles quoted fields with embedded delimiters, quotes and newlines, UTF-8 BOM, blank lines,
duplicate or empty header names (`a, a_2, col3`), and ragged rows.
Exit codes: 0 ok, 2 file not found / bad option, 3 decoding error, 4 malformed or empty CSV.

## Tests

```bash
pip install pytest
pytest -q
```

## License

MIT

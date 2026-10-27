#!/usr/bin/env python3
"""Convert a JSON file (array of flat objects) to CSV.

Missing keys are written as empty strings. Column order = first appearance.
Python 3.10+, standard library only.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from typing import Any, Iterable, TextIO


class ConversionError(Exception):
    """Raised for invalid input data."""


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        # Not flat: keep it lossless as compact JSON instead of crashing.
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def collect_columns(rows: Iterable[dict]) -> list[str]:
    seen: dict[str, None] = {}
    for row in rows:
        for key in row:
            seen.setdefault(str(key), None)
    return list(seen)


def convert(data: Any, out: TextIO, delimiter: str = ",", columns: list[str] | None = None) -> int:
    """Write `data` (list of dicts) as CSV to `out`. Returns number of rows written."""
    if not isinstance(data, list):
        raise ConversionError("top-level JSON value must be an array of objects")
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            raise ConversionError(f"element {i} is {type(row).__name__}, expected object")
    cols = columns or collect_columns(data)
    writer = csv.writer(out, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerow(cols)
    for row in data:
        str_row = {str(k): v for k, v in row.items()}
        writer.writerow([_cell(str_row.get(c, "")) for c in cols])
    return len(data)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Convert a JSON array of flat objects to CSV.")
    p.add_argument("input", help="input JSON file, or - for stdin")
    p.add_argument("-o", "--output", default="-", help="output CSV file (default: stdout)")
    p.add_argument("-d", "--delimiter", default=",", help="CSV delimiter (default: ,)")
    p.add_argument("-c", "--columns", help="comma-separated column order (default: auto)")
    p.add_argument("--encoding", default="utf-8")
    a = p.parse_args(argv)
    try:
        if a.input == "-":
            data = json.load(sys.stdin)
        else:
            with open(a.input, encoding=a.encoding) as f:
                data = json.load(f)
        cols = [c.strip() for c in a.columns.split(",")] if a.columns else None
        if a.output == "-":
            n = convert(data, sys.stdout, a.delimiter, cols)
        else:
            with open(a.output, "w", encoding=a.encoding, newline="") as f:
                n = convert(data, f, a.delimiter, cols)
    except FileNotFoundError as e:
        print(f"error: file not found: {e.filename}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as e:
        print(f"error: invalid JSON: {e}", file=sys.stderr)
        return 3
    except ConversionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 4
    print(f"wrote {n} rows", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

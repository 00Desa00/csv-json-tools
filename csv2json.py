#!/usr/bin/env python3
"""Convert CSV files of any structure to JSON.

- auto-detects the delimiter (, ; tab |) or accepts --delimiter
- handles quoted fields, embedded newlines/quotes, BOM, unicode
- output: array of objects (default), JSON Lines, or {"columns","rows"}
- optional type inference (int/float/bool/null), pretty or compact
- clear errors for empty files, ragged rows, bad encodings
Python 3.10+, standard library only.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from typing import Any

CANDIDATE_DELIMITERS = ",;\t|"


class CSVError(Exception):
    """Raised for invalid CSV input."""


def detect_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample, delimiters=CANDIDATE_DELIMITERS).delimiter
    except csv.Error:
        first = sample.splitlines()[0] if sample else ""
        counts = {d: first.count(d) for d in CANDIDATE_DELIMITERS}
        best = max(counts, key=counts.get)
        return best if counts[best] else ","


def infer(value: str) -> Any:
    v = value.strip()
    if v == "":
        return None
    low = v.lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "none"):
        return None
    digits = v.lstrip("+-")
    if len(digits) > 1 and digits[0] == "0" and digits[1] != ".":
        return value  # keep IDs / ZIP codes like "007" or "01067" as strings
    try:
        if digits.isdigit():
            return int(v)
        f = float(v)
        if f == f and f not in (float("inf"), float("-inf")):
            return f
    except ValueError:
        pass
    return value


def parse(text: str, delimiter: str | None = None, infer_types: bool = False,
          strict: bool = False, no_header: bool = False) -> tuple[list[str], list[list[Any]]]:
    if text.startswith("\ufeff"):
        text = text[1:]
    if not text.strip():
        raise CSVError("input is empty")
    delim = delimiter or detect_delimiter(text[:8192])
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delim, strict=True)
    try:
        rows = [r for r in reader if r and any(c.strip() for c in r)]
    except csv.Error as e:
        raise CSVError(f"malformed CSV at line {reader.line_num}: {e}") from e
    if not rows:
        raise CSVError("no data rows")
    if no_header:
        width = max(len(r) for r in rows)
        header = [f"col{i + 1}" for i in range(width)]
    else:
        header, rows = rows[0], rows[1:]
        header = _dedupe([h.strip() or f"col{i + 1}" for i, h in enumerate(header)])
    out = []
    for n, r in enumerate(rows, start=2 if not no_header else 1):
        if len(r) != len(header):
            if strict:
                raise CSVError(f"row {n} has {len(r)} fields, expected {len(header)}")
            r = (r + [""] * len(header))[: max(len(header), len(r))]
            if len(r) > len(header):
                header = header + [f"col{i + 1}" for i in range(len(header), len(r))]
        out.append([infer(c) for c in r] if infer_types else r)
    width = len(header)
    out = [(r + [None if infer_types else ""] * width)[:width] for r in out]
    return header, out


def _dedupe(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    res = []
    for n in names:
        if n in seen:
            seen[n] += 1
            res.append(f"{n}_{seen[n]}")
        else:
            seen[n] = 1
            res.append(n)
    return res


def render(header: list[str], rows: list[list[Any]], fmt: str = "records",
           indent: int | None = 2, sort_keys: bool = False, ascii_only: bool = False) -> str:
    kw = dict(ensure_ascii=ascii_only, sort_keys=sort_keys)
    if fmt == "jsonl":
        return "".join(json.dumps(dict(zip(header, r)), **kw) + "\n" for r in rows)
    if fmt == "table":
        obj: Any = {"columns": header, "rows": rows}
    else:
        obj = [dict(zip(header, r)) for r in rows]
    sep = None if indent else (",", ":")
    return json.dumps(obj, indent=indent, separators=sep, **kw) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Convert CSV of any structure to JSON.")
    p.add_argument("input", help="input CSV file, or - for stdin")
    p.add_argument("-o", "--output", default="-", help="output file (default: stdout)")
    p.add_argument("-d", "--delimiter", help="field delimiter (default: auto-detect); use \\t for tab")
    p.add_argument("-f", "--format", choices=["records", "jsonl", "table"], default="records")
    p.add_argument("--indent", type=int, default=2, help="indent spaces, 0 = compact (default: 2)")
    p.add_argument("--infer-types", action="store_true", help="convert numbers/booleans/empty to JSON types")
    p.add_argument("--no-header", action="store_true", help="first row is data; columns named col1..N")
    p.add_argument("--strict", action="store_true", help="fail on rows with wrong field count")
    p.add_argument("--sort-keys", action="store_true")
    p.add_argument("--ascii", action="store_true", help="escape non-ASCII characters")
    p.add_argument("--encoding", default="utf-8-sig")
    a = p.parse_args(argv)
    delim = a.delimiter.encode().decode("unicode_escape") if a.delimiter else None
    if delim is not None and len(delim) != 1:
        print("error: delimiter must be a single character", file=sys.stderr)
        return 2
    try:
        if a.input == "-":
            text = sys.stdin.read()
        else:
            with open(a.input, encoding=a.encoding, newline="") as f:
                text = f.read()
        header, rows = parse(text, delim, a.infer_types, a.strict, a.no_header)
        result = render(header, rows, a.format, a.indent or None, a.sort_keys, a.ascii)
        if a.output == "-":
            sys.stdout.write(result)
        else:
            with open(a.output, "w", encoding="utf-8") as f:
                f.write(result)
    except FileNotFoundError as e:
        print(f"error: file not found: {e.filename}", file=sys.stderr)
        return 2
    except UnicodeDecodeError as e:
        print(f"error: cannot decode input as {a.encoding}: {e.reason} (try --encoding latin-1)", file=sys.stderr)
        return 3
    except CSVError as e:
        print(f"error: {e}", file=sys.stderr)
        return 4
    print(f"converted {len(rows)} rows, {len(header)} columns", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

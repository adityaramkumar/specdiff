---
id: behaviors/csv-stats
version: "1.0.0"
status: approved
---

## CSV column statistics

Module `csv_stats.py` exposes two functions.

### `column_stats(path: str) -> dict[str, dict]`

Reads a CSV file whose first row is the header (standard CSV quoting rules).

- Missing file: `FileNotFoundError(f"no such file: {path}")`.
- No data rows (empty file or header only): `ValueError("no data rows")`.
- A data row with a different number of fields than the header:
  `ValueError(f"row {n}: expected {k} fields, got {m}")`, where `n` counts data
  rows from 1 (the header is not counted).

For each column, ignoring empty values (after stripping whitespace): if every
remaining value parses as a float, the result maps the column name to
`{"count": int, "min": float, "max": float, "mean": float}`, with `mean` rounded
to 2 decimal places. Columns with any non-numeric value, or no values at all,
are left out.

### `format_report(stats: dict) -> str`

Returns `json.dumps(stats, indent=2, sort_keys=True)` followed by a newline.

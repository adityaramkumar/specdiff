import csv
import json
from pathlib import Path


def column_stats(path: str) -> dict[str, dict]:
    if not Path(path).is_file():
        raise FileNotFoundError(f"no such file: {path}")
    with open(path, newline="") as f:
        rows = list(csv.reader(f))
    if len(rows) < 2:
        raise ValueError("no data rows")
    header, data = rows[0], rows[1:]
    for n, row in enumerate(data, 1):
        if len(row) != len(header):
            raise ValueError(f"row {n}: expected {len(header)} fields, got {len(row)}")
    stats = {}
    for i, name in enumerate(header):
        values = [row[i].strip() for row in data if row[i].strip()]
        try:
            numbers = [float(v) for v in values]
        except ValueError:
            continue
        if numbers:
            stats[name] = {
                "count": len(numbers),
                "min": min(numbers),
                "max": max(numbers),
                "mean": round(sum(numbers) / len(numbers), 2),
            }
    return stats


def format_report(stats: dict) -> str:
    return json.dumps(stats, indent=2, sort_keys=True) + "\n"

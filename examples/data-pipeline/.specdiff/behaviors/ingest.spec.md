---
id: behaviors/ingest
version: "1.0.1"
status: approved
depends_on:
  - contracts/schemas/raw-events
---

## Ingest Behavior

### Interface
- Function: `ingest(input_dir: str, output_dir: str) -> dict`
- Returns a summary dict: `{"valid": int, "invalid": int, "files": int}`

### Happy Path
- Scan `input_dir` for all `*.ndjson` files
- For each file: read line by line, validate each event against the raw events schema
- Valid events: write to `output_dir/valid/events.ndjson`
- Invalid events: write to `output_dir/dead-letter/events.ndjson` with an additional `_error` field

### Error Handling
- Input directory not found: raise `FileNotFoundError`
- No NDJSON files found: raise `ValueError("no .ndjson files found")`
- Empty files (0 bytes) are skipped silently

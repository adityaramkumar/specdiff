---
id: behaviors/load
version: "1.0.1"
status: approved
depends_on:
  - contracts/schemas/processed
---

## Load Behavior

### Interface
- Function: `load(input_dir: str, output_dir: str) -> dict`
- Returns a summary dict: `{"count": int, "partitions": int}`

### Happy Path
- Read all events from `input_dir/events.ndjson`
- Partition by `date` field: create `output_dir/{date}/events.ndjson`
- Within each partition: events sorted by `timestamp_utc` ascending

### Error Handling
- Input directory not found: raise `FileNotFoundError`
- No events file: raise `ValueError("no events found")`

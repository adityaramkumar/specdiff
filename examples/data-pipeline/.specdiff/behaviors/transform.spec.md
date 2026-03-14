---
id: behaviors/transform
version: "1.0.1"
status: approved
depends_on:
  - contracts/schemas/raw-events
  - contracts/schemas/processed
---

## Transform Behavior

### Interface
- Function: `transform(input_dir: str, output_dir: str) -> dict`
- Returns a summary dict: `{"count": int}`

### Happy Path
- Read all events from `input_dir/valid/events.ndjson`
- For each event:
  1. Convert timestamp to UTC, strip timezone offset
  2. Derive `date` (YYYY-MM-DD) and `hour` (0-23) from UTC timestamp
  3. Set `user_id` to `"anonymous"` if null; set `is_anonymous` accordingly
- Sort all events by `timestamp_utc` ascending
- Write to `output_dir/events.ndjson`

### Error Handling
- Input directory not found: raise `FileNotFoundError`
- No valid events file: raise `ValueError("no valid events found")`

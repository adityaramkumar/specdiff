---
id: behaviors/convert
version: "1.0.1"
status: approved
depends_on:
  - contracts/formats/csv
  - contracts/formats/json
---

## Convert Behavior

### Interface
- Function: `convert(input_path: str, output_path: str | None, detect_types: bool, compact: bool) -> str`
- Read CSV from `input_path`, convert to JSON
- If `output_path` is provided, write to that file and return the JSON string
- If `output_path` is None, just return the JSON string

### Happy Path
- Read and parse the CSV file according to the CSV format contract
- Convert each row to a JSON object using column headers as keys
- All values are strings by default
- If `detect_types` is True, apply type detection per the JSON format contract
- Write JSON array to output (pretty-printed with 2-space indent, or compact if flag is set)

### Error Handling
- File not found: raise `FileNotFoundError`
- Empty file: raise `ValueError("empty file")`
- Malformed CSV: raise `ValueError` with descriptive message

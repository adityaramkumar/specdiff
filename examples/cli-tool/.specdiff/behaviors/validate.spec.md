---
id: behaviors/validate
version: "1.0.1"
status: approved
depends_on:
  - contracts/formats/csv
---

## Validate Behavior

### Interface
- Function: `validate(input_path: str) -> tuple[bool, str]`
- Returns `(True, summary_message)` if valid, `(False, error_message)` if invalid

### Validation checks (in order)
1. File exists and is readable
2. File is not empty (0 bytes)
3. File size does not exceed 100 MB
4. Header row is present and parseable
5. Column names are unique (case-insensitive)

### Output
- Valid: returns `(True, "Valid: {N} rows, {M} columns")`
- Invalid: returns `(False, "{description}")` on first error found (fail-fast)

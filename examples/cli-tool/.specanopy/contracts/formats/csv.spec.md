---
id: contracts/formats/csv
version: "1.0.1"
status: approved
---

## CSV Format Contract

### Structure
- First row is always the header row containing column names
- Delimiter: comma (`,`)
- Quoting: fields containing commas or double quotes must be enclosed in double quotes
- Escape: double quotes within quoted fields are escaped by doubling (`""`)
- Encoding: UTF-8

### Constraints
- Maximum file size: 100 MB
- Column names must be unique (case-insensitive comparison)
- Empty files (0 bytes) are invalid
- Files with only a header row and no data rows are valid

### Error handling
All errors MUST use the built-in `ValueError` class. Do NOT create custom exception classes.
- Empty file: `raise ValueError("empty file")`
- Duplicate column names: `raise ValueError("duplicate column: {name}")`
- File too large: `raise ValueError("file too large")`

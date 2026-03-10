---
id: contracts/formats/csv
version: "1.0.0"
status: approved
---

## CSV Format Contract

### Structure
- First row is always the header row containing column names
- Delimiter: comma (`,`)
- Quoting: fields containing commas, newlines, or double quotes must be enclosed in double quotes
- Escape: double quotes within quoted fields are escaped by doubling (`""`)
- Parsing semantics follow RFC 4180 for commas, double quotes, escaped quotes, and embedded newlines
- Encoding: UTF-8
- Line endings: `\n` (Unix-style)

### Constraints
- Maximum file size: 100 MB
- Maximum columns: 1000
- Maximum row length: 1 MB measured as UTF-8 bytes of each physical CSV line before parsing
- The header row is subject to the same 1 MB row-length limit as data rows
- Column names must be unique (case-insensitive comparison)
- Empty files (0 bytes) are invalid
- Files with only a header row and no data rows are valid

### Error contract
- Invalid CSV files must fail with explicit custom error classes, not generic `ValueError` or generic `Error`
- Header row present but not parseable under the CSV quoting rules: raise `HeaderParseError`
- Duplicate column names (case-insensitive): raise `DuplicateHeaderError`
- More than 1000 columns in the header: raise `ColumnCountError`
- Any physical CSV line exceeding 1 MB before parsing: raise `RowLengthError`
- Any file exceeding 100 MB: raise `FileSizeError`
- Unclosed quote sequence anywhere in the file: raise `UnclosedQuoteError`
- Empty file (0 bytes): raise `EmptyFileError`
- `EmptyFileError` must be raised as its own custom error class, not encoded in a generic error message

### Parsing requirements
- The parser must correctly handle embedded newlines inside quoted fields
- Implementations must not split the entire file on `\n` before CSV parsing, because that breaks quoted multiline fields
- Streaming implementations may process byte-by-byte or character-by-character, but they must preserve RFC 4180 quoting behavior across line boundaries

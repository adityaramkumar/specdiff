---
id: contracts/formats/json
version: "1.0.0"
status: approved
---

## JSON Format Contract

### Structure for converted output
- Output is always a JSON array of objects
- Each object represents one row from the source
- Keys are the column names from the CSV header
- Values are strings by default; numeric detection is opt-in via `--detect-types` flag

### Type detection rules (when `--detect-types` is enabled)
- Integers: fields matching `^-?\d+$` become JSON numbers
- Floats: fields matching `^-?\d+\.\d+$` become JSON numbers
- Booleans: `true`/`false` (case-insensitive) become JSON booleans
- Null: empty fields become `null`
- Everything else remains a string

### Constraints
- Output encoding: UTF-8
- Pretty-printed with 2-space indentation by default
- Compact output available via `--compact` flag

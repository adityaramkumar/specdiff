---
id: contracts/schemas/raw-events
version: "1.0.0"
status: approved
---

## Raw Events Schema

### Event Object (as received from source)
```json
{
  "event_id": "string (UUID)",
  "event_type": "string (one of: page_view, click, purchase, signup)",
  "timestamp": "string (ISO 8601 with timezone)",
  "user_id": "string (UUID, nullable for anonymous events)",
  "properties": "object (arbitrary key-value pairs)",
  "source": "string (one of: web, mobile, api)"
}
```

### Input format
- Events arrive as newline-delimited JSON (NDJSON), one event per line
- Maximum event size: 64 KB per line
- Files may contain 0 to 10 million events
- Events are NOT guaranteed to be in chronological order

### Validation rules
- `event_id` must be a valid UUID v4
- `event_type` must be one of the allowed values
- `timestamp` must be a valid ISO 8601 datetime with timezone
- `user_id` if present must be a valid UUID v4
- `properties` must be a JSON object (not array, not null)
- `source` must be one of the allowed values
- Missing required fields are validation failures, not parser crashes
- Events failing validation are written to a dead-letter file, not discarded silently
- Malformed JSON lines are treated as invalid events and must be routed to dead-letter handling
- Events exceeding 64 KB are treated as invalid events and must be routed to dead-letter handling
- Parsing and validation helpers must report these failures back to the caller instead of terminating the process

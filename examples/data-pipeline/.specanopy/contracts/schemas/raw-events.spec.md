---
id: contracts/schemas/raw-events
version: "1.0.1"
status: approved
---

## Raw Events Schema

### Event Object
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

### Validation rules
- `event_id` must be present and a valid UUID
- `event_type` must be one of the allowed values
- `timestamp` must be a valid ISO 8601 datetime string
- `source` must be one of the allowed values
- `properties` must be a dict (not array, not null)
- Invalid events are routed to a dead-letter output, not discarded silently

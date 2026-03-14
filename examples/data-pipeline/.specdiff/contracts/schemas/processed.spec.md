---
id: contracts/schemas/processed
version: "1.0.1"
status: approved
---

## Processed Events Schema

### Processed Event Object
```json
{
  "event_id": "string (UUID, from raw event)",
  "event_type": "string (from raw event)",
  "timestamp_utc": "string (ISO 8601, always UTC)",
  "date": "string (YYYY-MM-DD, derived from timestamp_utc)",
  "hour": "integer (0-23, derived from timestamp_utc)",
  "user_id": "string (UUID or 'anonymous')",
  "is_anonymous": "boolean",
  "source": "string (from raw event)",
  "properties": "object (from raw event)"
}
```

### Output format
- Partitioned by date: `{date}/events.ndjson`
- Each partition file contains events sorted by `timestamp_utc` ascending

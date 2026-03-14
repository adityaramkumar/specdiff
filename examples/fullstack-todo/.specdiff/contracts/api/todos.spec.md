---
id: contracts/api/todos
version: "1.0.0"
status: approved
---

## Todos API Contract

### Todo Object
```json
{
  "id": "uuid",
  "title": "string (1-200 characters)",
  "completed": "boolean",
  "created_at": "ISO 8601 datetime",
  "updated_at": "ISO 8601 datetime"
}
```

### Endpoints

**GET /api/todos**
- Returns: `{ "todos": Todo[], "count": number }`
- Query params: `?completed=true|false` (optional filter)

**POST /api/todos**
- Request: `{ "title": "string" }`
- Success (201): returns the created Todo object
- Error (422): `{ "error": "title_required" }` if title is empty
- Error (422): `{ "error": "title_too_long" }` if title exceeds 200 characters

**PUT /api/todos/:id**
- Request: `{ "title?": "string", "completed?": "boolean" }`
- Success (200): returns the updated Todo object
- Error (404): `{ "error": "todo_not_found" }`
- Error (422): `{ "error": "title_too_long" }` if title exceeds 200 characters

**DELETE /api/todos/:id**
- Success (204): no body
- Error (404): `{ "error": "todo_not_found" }`

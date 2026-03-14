---
id: behaviors/users/profile
version: "1.0.1"
status: approved
depends_on:
  - contracts/api/users
---

## User Profile Behavior

### GET /api/users/:id
- Look up user by ID from an in-memory store
- Return HTTP 200 with `{ "id", "email", "name", "created_at" }` (no password_hash)
- If user not found: return HTTP 404 with `{ "error": "user_not_found" }`

### PUT /api/users/:id
- Update the user's name field
- Request body: `{ "name": "string" }`
- Return HTTP 200 with updated user object
- Empty or missing name: return HTTP 422 with `{ "error": "name_required" }`
- Name longer than 100 characters: return HTTP 422 with `{ "error": "name_too_long" }`

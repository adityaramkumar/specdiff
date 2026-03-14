---
id: contracts/api/users
version: "1.0.1"
status: approved
---

## Users API Contract

### User Object
```json
{
  "id": "uuid",
  "email": "string",
  "name": "string",
  "password_hash": "string (hashed password, never returned in API responses)",
  "created_at": "ISO 8601 datetime"
}
```

### POST /api/auth/login
- Request: `{ "email": "string", "password": "string" }`
- Success (200): `{ "token": "string", "redirect": "/dashboard" }`
- Error 422: `{ "error": "invalid_email_format" }`
- Error 401: `{ "error": "invalid_credentials" }`

### POST /api/auth/signup
- Request: `{ "email": "string", "password": "string", "name": "string" }`
- Success (201): `{ "id": "uuid", "email": "string" }`
- Error 422: `{ "error": "invalid_email_format" }` or `{ "error": "password_too_weak" }`
- Error 409: `{ "error": "email_already_registered" }`

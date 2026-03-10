---
id: contracts/api/users
version: "1.0.0"
status: approved
---

## Users API Contract

### User Object

```json
{
  "id": "uuid",
  "email": "string (RFC 5322)",
  "password_hash": "string (bcrypt)",
  "created_at": "ISO 8601 datetime",
  "locked_until": "ISO 8601 datetime | null"
}
```

### POST /api/auth/login

**Request:**
```json
{ "email": "string", "password": "string" }
```

**Success (200):**
```json
{ "token": "JWT string", "redirect": "/dashboard" }
```

**Errors:**
- 422: `{ "error": "invalid_email_format" }`
- 401: `{ "error": "invalid_credentials" }`
- 403: `{ "error": "account_locked" }`

### POST /api/auth/signup

**Request:**
```json
{ "email": "string", "password": "string", "name": "string" }
```

**Success (201):**
```json
{ "id": "uuid", "email": "string" }
```

**Errors:**
- 422: `{ "error": "invalid_email_format" }` or `{ "error": "password_too_weak" }`
- 409: `{ "error": "email_already_registered" }`

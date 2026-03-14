---
id: behaviors/auth/login
version: "1.0.1"
status: approved
depends_on:
  - contracts/api/users
---

## Login Behavior

### Happy Path
- User submits valid email and password
- System validates credentials against an in-memory user store
- On success: return a JWT token string and redirect path "/dashboard"

### Error Handling
- Invalid email format: return HTTP 422 with `{ "error": "invalid_email_format" }`
- Wrong password: return HTTP 401 with `{ "error": "invalid_credentials" }`
- Any unexpected error: return HTTP 500 with `{ "error": "internal_error" }`

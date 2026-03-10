---
id: behaviors/auth/login
version: "1.0.0"
parent: auth
status: approved
depends_on:
  - contracts/api/users
---

## Login Behavior

### Happy Path
- User submits valid email and password
- System validates credentials against the user store
- On success: return a JWT with `sub` set to the user ID, `exp` set to 1 hour from now
- Redirect to `/dashboard`

### Error Handling
- Invalid email format: return HTTP 422 with `{ "error": "invalid_email_format" }`
- Wrong password: return HTTP 401 with `{ "error": "invalid_credentials" }`
- Account locked: return HTTP 403 with `{ "error": "account_locked" }`

### Rate Limiting
- After 5 failed attempts within 10 minutes, lock the account
- Lock duration: 30 minutes
- Unlock method: automatic after lock duration expires

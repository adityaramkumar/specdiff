---
id: behaviors/auth/signup
version: "1.0.0"
status: approved
depends_on:
  - contracts/api/users
---

## Signup Behavior

### Happy Path
- User submits valid email, password, and name
- System checks email is not already registered
- Password must be at least 12 characters with 1 uppercase, 1 digit, 1 special character
- On success: create user record, return HTTP 201 with user id and email

### Error Handling
- Invalid email format: return HTTP 422 with `{ "error": "invalid_email_format" }`
- Weak password: return HTTP 422 with `{ "error": "password_too_weak" }`
- Email already registered: return HTTP 409 with `{ "error": "email_already_registered" }`
- Any unexpected error: return HTTP 500 with `{ "error": "internal_error" }`

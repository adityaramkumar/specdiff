// generated_from: behaviors/auth/login
// spec_hash: 00335c53ca3b6c799e009972b346695606d4fcc3a9ac7f85e4fc5ef7179f7657
// generated_at: 2026-03-10T09:00:14.215136+00:00
// agent: implementation-agent
export interface UserCredentials {
  email: string;
  password: string;
}

export interface LoginResult {
  token: string;
  redirect: string;
}

export type LoginError = 'invalid_email_format' | 'invalid_credentials' | 'account_locked';
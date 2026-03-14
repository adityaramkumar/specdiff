// generated_from: behaviors/auth/login
// spec_hash: 3e8460ea156b262964d71466b05a1aee93705931a00932181862872401776894
// generated_at: 2026-03-14T21:58:57.672721+00:00
// agent: implementation-agent
import { login, LoginError } from '../../domain/auth/login.service';
import { isValidEmail } from '../validation/email.validator';

export interface ApiResponse { status: number; body: object; }

export async function handleLogin(req: { email: string; password: string }): Promise<ApiResponse> {
  if (!isValidEmail(req.email)) {
    return { status: 422, body: { error: 'invalid_email_format' } };
  }

  try {
    const result = await login(req.email, req.password);
    return { status: 200, body: result };
  } catch (error) {
    if (error instanceof LoginError) {
      return { status: error.status, body: { error: error.code } };
    }
    return { status: 500, body: { error: 'internal_error' } };
  }
}

export async function handleSignup(req: { email: string; password: string; name: string }): Promise<ApiResponse> {
  return { status: 501, body: { error: 'not_implemented' } };
}
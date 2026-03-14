// generated_from: behaviors/auth/login
// spec_hash: 3e8460ea156b262964d71466b05a1aee93705931a00932181862872401776894
// generated_at: 2026-03-14T21:58:57.679537+00:00
// agent: testing-agent
import { describe, it, expect, vi } from 'vitest';
import { handleLogin } from '../../infrastructure/api/auth.controller';
import * as loginService from '../../domain/auth/login.service';
import * as emailValidator from '../../infrastructure/validation/email.validator';

vi.mock('../../domain/auth/login.service');
vi.mock('../../infrastructure/validation/email.validator');

describe('auth controller login', () => {
  it('returns 422 for invalid email format', async () => {
    vi.mocked(emailValidator.isValidEmail).mockReturnValue(false);

    const response = await handleLogin({ email: 'bad-email', password: 'password' });
    
    expect(response.status).toBe(422);
    expect(response.body).toEqual({ error: 'invalid_email_format' });
  });

  it('returns 200 on successful login', async () => {
    vi.mocked(emailValidator.isValidEmail).mockReturnValue(true);
    vi.mocked(loginService.login).mockResolvedValue({ token: 'jwt', redirect: '/dashboard' });

    const response = await handleLogin({ email: 'test@test.com', password: 'password' });

    expect(response.status).toBe(200);
    expect(response.body).toEqual({ token: 'jwt', redirect: '/dashboard' });
  });

  it('returns 401 on authentication failure', async () => {
    vi.mocked(emailValidator.isValidEmail).mockReturnValue(true);
    vi.mocked(loginService.login).mockRejectedValue(new loginService.LoginError('invalid_credentials', 401));

    const response = await handleLogin({ email: 'test@test.com', password: 'wrong' });

    expect(response.status).toBe(401);
    expect(response.body).toEqual({ error: 'invalid_credentials' });
  });

  it('returns 500 for unexpected errors', async () => {
    vi.mocked(emailValidator.isValidEmail).mockReturnValue(true);
    vi.mocked(loginService.login).mockRejectedValue(new Error('crash'));

    const response = await handleLogin({ email: 'test@test.com', password: 'password' });

    expect(response.status).toBe(500);
    expect(response.body).toEqual({ error: 'internal_error' });
  });
});
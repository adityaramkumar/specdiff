// generated_from: behaviors/auth/signup
// spec_hash: f186382487e04177e71760b73b531d3b0bea1d2d470e71368e2f698403097c3a
// generated_at: 2026-03-14T21:59:11.607966+00:00
// agent: testing-agent
import { describe, it, expect, vi } from 'vitest';
import { handleSignup } from '../../../infrastructure/web/signup.controller';
import * as signupService from '../../../domain/signup/signup.service';

vi.mock('../../../domain/signup/signup.service');

describe('handleSignup', () => {
  it('returns 201 when registration is successful', async () => {
    const req = { body: { email: 't@t.com', password: 'Password123!', name: 'T' } } as any;
    const res = { status: vi.fn().mockReturnThis(), json: vi.fn() } as any;

    vi.mocked(signupService.registerUser).mockResolvedValue({ id: '123', email: 't@t.com' });

    await handleSignup(req, res);

    expect(res.status).toHaveBeenCalledWith(201);
    expect(res.json).toHaveBeenCalledWith({ id: '123', email: 't@t.com' });
  });

  it('returns 422 for weak password', async () => {
    const req = { body: { email: 't@t.com', password: '123', name: 'T' } } as any;
    const res = { status: vi.fn().mockReturnThis(), json: vi.fn() } as any;

    vi.mocked(signupService.registerUser).mockRejectedValue('password_too_weak');

    await handleSignup(req, res);

    expect(res.status).toHaveBeenCalledWith(422);
    expect(res.json).toHaveBeenCalledWith({ error: 'password_too_weak' });
  });

  it('returns 409 when email already exists', async () => {
    const req = { body: { email: 't@t.com', password: 'Password123!', name: 'T' } } as any;
    const res = { status: vi.fn().mockReturnThis(), json: vi.fn() } as any;

    vi.mocked(signupService.registerUser).mockRejectedValue('email_already_registered');

    await handleSignup(req, res);

    expect(res.status).toHaveBeenCalledWith(409);
    expect(res.json).toHaveBeenCalledWith({ error: 'email_already_registered' });
  });

  it('returns 500 for unexpected errors', async () => {
    const req = { body: { email: 't@t.com', password: 'Password123!', name: 'T' } } as any;
    const res = { status: vi.fn().mockReturnThis(), json: vi.fn() } as any;

    vi.mocked(signupService.registerUser).mockRejectedValue(new Error('DB crash'));

    await handleSignup(req, res);

    expect(res.status).toHaveBeenCalledWith(500);
    expect(res.json).toHaveBeenCalledWith({ error: 'internal_error' });
  });
});
// generated_from: behaviors/auth/signup
// spec_hash: f186382487e04177e71760b73b531d3b0bea1d2d470e71368e2f698403097c3a
// generated_at: 2026-03-14T21:59:11.602014+00:00
// agent: implementation-agent
import { describe, it, expect, vi } from 'vitest';
import { handleSignup } from './signup.controller';
import * as service from '../../domain/signup/signup.service';

describe('handleSignup', () => {
  it('returns 201 on success', async () => {
    const req = { body: { email: 'a@b.com', password: 'P1!', name: 'N' } } as any;
    const res = { status: vi.fn().mockReturnThis(), json: vi.fn() } as any;
    vi.spyOn(service, 'registerUser').mockResolvedValue({ id: '1', email: 'a@b.com' });
    await handleSignup(req, res);
    expect(res.status).toHaveBeenCalledWith(201);
  });
});
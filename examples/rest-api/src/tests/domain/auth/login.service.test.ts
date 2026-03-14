// generated_from: behaviors/auth/login
// spec_hash: 3e8460ea156b262964d71466b05a1aee93705931a00932181862872401776894
// generated_at: 2026-03-14T21:58:57.673888+00:00
// agent: testing-agent
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { login, LoginError } from '../../domain/auth/login.service';
import { userStore } from '../../domain/auth/user.store';
import * as jwtProvider from '../../infrastructure/security/jwt.provider';

vi.mock('../../domain/auth/user.store', () => ({
  userStore: { findByEmail: vi.fn() }
}));

vi.mock('../../infrastructure/security/jwt.provider', () => ({
  generateToken: vi.fn()
}));

describe('login service', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns token and redirect on valid credentials', async () => {
    const mockUser = { id: '123', email: 'test@example.com', password_hash: 'hashed_password' };
    vi.mocked(userStore.findByEmail).mockResolvedValue(mockUser);
    vi.mocked(jwtProvider.generateToken).mockReturnValue('mocked_jwt');

    const result = await login('test@example.com', 'plain_password');
    
    expect(result).toEqual({ token: 'mocked_jwt', redirect: '/dashboard' });
  });

  it('throws LoginError 401 when password does not match', async () => {
    vi.mocked(userStore.findByEmail).mockResolvedValue({
      id: '123',
      email: 'test@example.com',
      password_hash: 'wrong_hash'
    });

    await expect(login('test@example.com', 'wrong_password')).rejects.toThrow(new LoginError('invalid_credentials', 401));
  });

  it('throws LoginError 401 when user is not found', async () => {
    vi.mocked(userStore.findByEmail).mockResolvedValue(null);

    await expect(login('unknown@example.com', 'password')).rejects.toThrow(new LoginError('invalid_credentials', 401));
  });
});
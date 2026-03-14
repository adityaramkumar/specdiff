// generated_from: behaviors/auth/signup
// spec_hash: f186382487e04177e71760b73b531d3b0bea1d2d470e71368e2f698403097c3a
// generated_at: 2026-03-14T21:59:11.594385+00:00
// agent: implementation-agent
import { describe, it, expect, vi } from 'vitest';
import { registerUser } from './signup.service';
import { userRepository } from '../../infrastructure/persistence/user.repository';

vi.mock('../../infrastructure/persistence/user.repository');

describe('registerUser', () => {
  it('registers a user successfully', async () => {
    vi.mocked(userRepository.findByEmail).mockResolvedValue(null);
    vi.mocked(userRepository.create).mockResolvedValue({
      id: 'uuid', email: 'test@test.com', name: 'Test', password_hash: '...', created_at: '2023-01-01'
    });
    const res = await registerUser({ email: 'test@test.com', password: 'Password123!', name: 'Test' });
    expect(res.id).toBe('uuid');
  });
});
// generated_from: contracts/api/users
// spec_hash: f40252d816057e05a68d187a6823e059435ed25eb34fc5abde3ceba2491cd49a
// generated_at: 2026-03-14T21:58:45.334240+00:00
// agent: testing-agent
import { describe, it, expect } from 'vitest';
import { hashPassword, verifyPassword } from '../auth/password.utils';

describe('password.utils unit tests', () => {
  it('should hash a password and verify it successfully', async () => {
    const password = 'mySecretPassword123';
    const hash = await hashPassword(password);
    
    expect(hash).not.toBe(password);
    const isValid = await verifyPassword(password, hash);
    expect(isValid).toBe(true);
  });

  it('should return false for incorrect password verification', async () => {
    const password = 'correctPassword';
    const hash = await hashPassword(password);
    
    const isValid = await verifyPassword('wrongPassword', hash);
    expect(isValid).toBe(false);
  });
});
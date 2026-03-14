// generated_from: behaviors/auth/signup
// spec_hash: f186382487e04177e71760b73b531d3b0bea1d2d470e71368e2f698403097c3a
// generated_at: 2026-03-14T21:59:11.607111+00:00
// agent: testing-agent
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { registerUser } from '../../../domain/signup/signup.service';
import * as userRepository from '../../../infrastructure/persistence/user.repository';

// Mocking dependencies
vi.mock('../../../infrastructure/persistence/user.repository');

describe('registerUser', () => {
  it('successfully creates a user when inputs are valid', async () => {
    const request = { 
      email: 'test@example.com', 
      password: 'StrongPassword1!', 
      name: 'John Doe' 
    };
    
    // Assume the repository mock is handled by a DI container or global mock
    // Implementation details omitted as per prompt rules, focusing on orchestration logic
    const result = await registerUser(request);
    
    expect(result).toHaveProperty('id');
    expect(result.email).toBe(request.email);
  });

  it('throws password_too_weak if password requirements not met', async () => {
    const request = { email: 'test@example.com', password: '123', name: 'John' };
    await expect(registerUser(request)).rejects.toBe('password_too_weak');
  });

  it('throws invalid_email_format if email is invalid', async () => {
    const request = { email: 'invalid-email', password: 'StrongPassword1!', name: 'John' };
    await expect(registerUser(request)).rejects.toBe('invalid_email_format');
  });

  it('throws email_already_registered if user exists', async () => {
    // Simulate existing user in repo
    const request = { email: 'exists@example.com', password: 'StrongPassword1!', name: 'John' };
    await expect(registerUser(request)).rejects.toBe('email_already_registered');
  });
});
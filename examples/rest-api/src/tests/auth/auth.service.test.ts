// generated_from: contracts/api/users
// spec_hash: f40252d816057e05a68d187a6823e059435ed25eb34fc5abde3ceba2491cd49a
// generated_at: 2026-03-14T21:58:45.333285+00:00
// agent: testing-agent
import { describe, it, expect, vi } from 'vitest';
import { loginUser, signupUser } from '../auth/auth.service';

describe('auth.service unit tests', () => {
  describe('loginUser', () => {
    it('should return token and redirect on valid credentials', async () => {
      // Mock implementation detail: actual logic handled by service
      const result = await loginUser('test@example.com', 'password123');
      expect(result).toEqual({ token: expect.any(String), redirect: '/dashboard' });
    });

    it('should throw invalid_credentials for wrong password', async () => {
      await expect(loginUser('test@example.com', 'wrong')).rejects.toThrow('invalid_credentials');
    });

    it('should throw invalid_email_format for malformed email', async () => {
      await expect(loginUser('bad-email', 'password123')).rejects.toThrow('invalid_email_format');
    });
  });

  describe('signupUser', () => {
    it('should return id and email on successful signup', async () => {
      const result = await signupUser('new@example.com', 'SecurePass123!', 'John Doe');
      expect(result).toEqual({ id: expect.any(String), email: 'new@example.com' });
    });

    it('should throw email_already_registered when email exists', async () => {
      await expect(signupUser('existing@example.com', 'SecurePass123!', 'John')).rejects.toThrow('email_already_registered');
    });

    it('should throw password_too_weak for weak passwords', async () => {
      await expect(signupUser('new@example.com', '123', 'John')).rejects.toThrow('password_too_weak');
    });

    it('should throw invalid_email_format for malformed email', async () => {
      await expect(signupUser('invalid-email', 'SecurePass123!', 'John')).rejects.toThrow('invalid_email_format');
    });
  });
});
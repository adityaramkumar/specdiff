// generated_from: behaviors/auth/signup
// spec_hash: f186382487e04177e71760b73b531d3b0bea1d2d470e71368e2f698403097c3a
// generated_at: 2026-03-14T21:59:11.604742+00:00
// agent: testing-agent
import { describe, it, expect } from 'vitest';
import { isPasswordValid } from '../../../domain/signup/password.validator';

describe('isPasswordValid', () => {
  it('returns false for passwords shorter than 12 characters', () => {
    expect(isPasswordValid('Ab1!5678901')).toBe(false);
  });

  it('returns false for missing uppercase letter', () => {
    expect(isPasswordValid('abcdef123456!')).toBe(false);
  });

  it('returns false for missing digit', () => {
    expect(isPasswordValid('Abcdefghijk!')).toBe(false);
  });

  it('returns false for missing special character', () => {
    expect(isPasswordValid('Abcdef1234567')).toBe(false);
  });

  it('returns true for valid password (>=12 chars, 1 upper, 1 digit, 1 special)', () => {
    expect(isPasswordValid('Password123!')).toBe(true);
  });
});
// generated_from: behaviors/auth/signup
// spec_hash: f186382487e04177e71760b73b531d3b0bea1d2d470e71368e2f698403097c3a
// generated_at: 2026-03-14T21:59:11.592140+00:00
// agent: implementation-agent
import { describe, it, expect } from 'vitest';
import { isPasswordValid } from './password.validator';

describe('isPasswordValid', () => {
  it('validates password complexity correctly', () => {
    expect(isPasswordValid('Abc12345678!')).toBe(true);
    expect(isPasswordValid('abc12345678!')).toBe(false); // No uppercase
    expect(isPasswordValid('ABCDEFGHIJKL')).toBe(false); // No digit/special
    expect(isPasswordValid('Short1!')).toBe(false); // Too short
  });
});
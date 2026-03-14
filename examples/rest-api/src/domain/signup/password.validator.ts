// generated_from: behaviors/auth/signup
// spec_hash: f186382487e04177e71760b73b531d3b0bea1d2d470e71368e2f698403097c3a
// generated_at: 2026-03-14T21:59:11.590854+00:00
// agent: implementation-agent
/**
 * Validates password complexity: >=12 chars, 1 uppercase, 1 digit, 1 special character.
 * @returns true if valid, false otherwise.
 */
export function isPasswordValid(password: string): boolean {
  if (password.length < 12) return false;
  const hasUppercase = /[A-Z]/.test(password);
  const hasDigit = /[0-9]/.test(password);
  const hasSpecial = /[^A-Za-z0-9]/.test(password);
  return hasUppercase && hasDigit && hasSpecial;
}
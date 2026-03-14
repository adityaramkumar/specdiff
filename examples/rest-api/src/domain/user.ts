// generated_from: behaviors/users/profile
// spec_hash: 0b617acb52c2f132b799bc16470845b2594558e0726d102a13875aa879178b29
// generated_at: 2026-03-14T21:59:24.901020+00:00
// agent: implementation-agent
export interface User {
  id: string;
  email: string;
  name: string;
  password_hash: string;
  created_at: string;
}

export type UserProfile = Omit<User, 'password_hash'>;

export function validateName(name: string): 'valid' | 'required' | 'too_long' {
  if (!name || name.trim().length === 0) return 'required';
  if (name.length > 100) return 'too_long';
  return 'valid';
}

export function isEmailValid(email: string): boolean {
  return /^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$/.test(email);
}
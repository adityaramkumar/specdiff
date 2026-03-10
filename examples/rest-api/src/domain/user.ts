// generated_from: behaviors/users/profile
// spec_hash: d1f76ac9b12b1560185010f04ecae9a79ca4e17e78accdbabc8ee582b60bbd58
// generated_at: 2026-03-10T09:00:31.838622+00:00
// agent: implementation-agent
export interface User {
  id: string;
  email: string;
  password_hash: string;
  name: string;
  created_at: string;
  locked_until: string | null;
}

export type UserProfile = Omit<User, 'password_hash'>;
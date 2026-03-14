// generated_from: contracts/api/users
// spec_hash: f40252d816057e05a68d187a6823e059435ed25eb34fc5abde3ceba2491cd49a
// generated_at: 2026-03-14T21:58:45.323466+00:00
// agent: implementation-agent
export interface User {
  id: string;
  email: string;
  name: string;
  password_hash: string;
  created_at: string;
}

export type UserPublicProfile = Omit<User, 'password_hash'>;
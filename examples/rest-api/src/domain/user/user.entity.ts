// generated_from: contracts/api/users
// spec_hash: 5cf5cc538d1b81c8c474dcd47c648ab4c75be2232eb84c596a9c8849e1842678
// generated_at: 2026-03-10T09:00:06.432869+00:00
// agent: implementation-agent
export interface User {
  id: string;
  email: string;
  password_hash: string;
  created_at: string;
  locked_until: string | null;
}
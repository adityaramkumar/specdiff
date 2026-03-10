// generated_from: behaviors/auth/signup
// spec_hash: 76de4dd5faf70d2285d59b7b3320eddbd2b2bb65e458c3cc5573b304b7c759d4
// generated_at: 2026-03-10T09:00:21.226835+00:00
// agent: implementation-agent
export interface UserRecord {
  id: string;
  email: string;
  password_hash: string;
}

export interface SignupRepository {
  findByEmail(email: string): Promise<UserRecord | null>;
  create(user: Omit<UserRecord, 'id'>): Promise<UserRecord>;
}
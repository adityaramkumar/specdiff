// generated_from: behaviors/auth/signup
// spec_hash: f186382487e04177e71760b73b531d3b0bea1d2d470e71368e2f698403097c3a
// generated_at: 2026-03-14T21:59:11.595272+00:00
// agent: implementation-agent
export interface UserEntity { id: string; email: string; name: string; password_hash: string; created_at: string; }

export interface UserRepository {
  findByEmail(email: string): Promise<UserEntity | null>;
  create(user: Omit<UserEntity, 'id' | 'created_at'>): Promise<UserEntity>;
}

// Mock implementation for infra layer
export const userRepository: UserRepository = {
  findByEmail: async (email) => null,
  create: async (user) => ({ ...user, id: '1', created_at: new Date().toISOString() })
};
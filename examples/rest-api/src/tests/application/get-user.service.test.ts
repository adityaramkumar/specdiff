// generated_from: behaviors/users/profile
// spec_hash: 0b617acb52c2f132b799bc16470845b2594558e0726d102a13875aa879178b29
// generated_at: 2026-03-14T21:59:24.911489+00:00
// agent: testing-agent
import { describe, it, expect, vi } from 'vitest';
import { getUserProfile } from '../../application/get-user.service';
import { UserRepository } from '../../domain/user.repository';
import { User } from '../../domain/user';

describe('getUserProfile', () => {
  it('should return user profile without password_hash if user exists', async () => {
    const mockUser: User = {
      id: 'uuid-1',
      email: 'test@example.com',
      name: 'John Doe',
      password_hash: 'secret',
      created_at: '2023-01-01T00:00:00Z',
    };

    const repository: UserRepository = {
      findById: vi.fn().mockResolvedValue(mockUser),
      update: vi.fn(),
      save: vi.fn(),
    };

    const result = await getUserProfile('uuid-1', repository);

    expect(result).toEqual({
      id: 'uuid-1',
      email: 'test@example.com',
      name: 'John Doe',
      created_at: '2023-01-01T00:00:00Z',
    });
    expect(result).not.toHaveProperty('password_hash');
  });

  it('should throw user_not_found error when user does not exist', async () => {
    const repository: UserRepository = {
      findById: vi.fn().mockResolvedValue(null),
      update: vi.fn(),
      save: vi.fn(),
    };

    await expect(getUserProfile('uuid-missing', repository)).rejects.toThrow('user_not_found');
  });
});
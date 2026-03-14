// generated_from: behaviors/users/profile
// spec_hash: 0b617acb52c2f132b799bc16470845b2594558e0726d102a13875aa879178b29
// generated_at: 2026-03-14T21:59:24.913162+00:00
// agent: testing-agent
import { describe, it, expect, vi } from 'vitest';
import { updateUserName } from '../../application/update-user.service';
import { UserRepository } from '../../domain/user.repository';
import { User } from '../../domain/user';

describe('updateUserName', () => {
  const mockUser: User = {
    id: 'uuid-1',
    email: 'test@example.com',
    name: 'Old Name',
    password_hash: 'secret',
    created_at: '2023-01-01T00:00:00Z',
  };

  const repository: UserRepository = {
    findById: vi.fn().mockResolvedValue(mockUser),
    update: vi.fn().mockImplementation((id, data) => Promise.resolve({ ...mockUser, name: data.name })),
    save: vi.fn(),
  };

  it('should update name successfully', async () => {
    const result = await updateUserName('uuid-1', 'New Name', repository);
    expect(result.name).toBe('New Name');
    expect(repository.update).toHaveBeenCalledWith('uuid-1', { name: 'New Name' });
  });

  it('should throw name_required if name is empty', async () => {
    await expect(updateUserName('uuid-1', '', repository)).rejects.toThrow('name_required');
  });

  it('should throw name_too_long if name exceeds 100 chars', async () => {
    const longName = 'a'.repeat(101);
    await expect(updateUserName('uuid-1', longName, repository)).rejects.toThrow('name_too_long');
  });
});
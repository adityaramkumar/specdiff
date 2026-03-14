// generated_from: behaviors/users/profile
// spec_hash: 0b617acb52c2f132b799bc16470845b2594558e0726d102a13875aa879178b29
// generated_at: 2026-03-14T21:59:24.908032+00:00
// agent: implementation-agent
import { UserProfile, validateName } from '../domain/user';
import { UserRepository } from '../domain/user.repository';

export async function updateUserName(id: string, name: string, repository: UserRepository): Promise<UserProfile> {
  const validation = validateName(name);
  if (validation === 'required') throw new Error('name_required');
  if (validation === 'too_long') throw new Error('name_too_long');

  const updatedUser = await repository.update(id, { name });
  const { password_hash, ...profile } = updatedUser;
  return profile;
}
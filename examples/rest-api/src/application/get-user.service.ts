// generated_from: behaviors/users/profile
// spec_hash: 0b617acb52c2f132b799bc16470845b2594558e0726d102a13875aa879178b29
// generated_at: 2026-03-14T21:59:24.904762+00:00
// agent: implementation-agent
import { UserProfile } from '../domain/user';
import { UserRepository } from '../domain/user.repository';

export async function getUserProfile(id: string, repository: UserRepository): Promise<UserProfile> {
  const user = await repository.findById(id);
  if (!user) {
    throw new Error('user_not_found');
  }
  const { password_hash, ...profile } = user;
  return profile;
}
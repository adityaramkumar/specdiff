// generated_from: behaviors/users/profile
// spec_hash: d1f76ac9b12b1560185010f04ecae9a79ca4e17e78accdbabc8ee582b60bbd58
// generated_at: 2026-03-10T09:00:31.838622+00:00
// agent: implementation-agent
import { UserRepository } from '../domain/user.repository';
import { UserProfile } from '../domain/user';

export class UserService {
  constructor(private userRepository: UserRepository) {}

  async getProfile(id: string, authenticatedUserId: string): Promise<UserProfile> {
    if (id !== authenticatedUserId) {
      throw { status: 403, error: 'forbidden' };
    }

    const user = await this.userRepository.findById(id);
    if (!user) {
      throw { status: 404, error: 'user_not_found' };
    }

    const { password_hash, ...profile } = user;
    return profile;
  }

  async updateProfile(id: string, authenticatedUserId: string, name: string): Promise<UserProfile> {
    if (id !== authenticatedUserId) {
      throw { status: 403, error: 'forbidden' };
    }

    if (!name || name.trim() === '') {
      throw { status: 422, error: 'name_required' };
    }

    if (name.length > 100) {
      throw { status: 422, error: 'name_too_long' };
    }

    const updatedUser = await this.userRepository.updateName(id, name);
    const { password_hash, ...profile } = updatedUser;
    return profile;
  }
}
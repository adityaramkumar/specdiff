// generated_from: behaviors/users/profile
// spec_hash: 0b617acb52c2f132b799bc16470845b2594558e0726d102a13875aa879178b29
// generated_at: 2026-03-14T21:59:24.903836+00:00
// agent: implementation-agent
import { User } from '../domain/user';
import { UserRepository } from '../domain/user.repository';

export class InMemoryUserRepository implements UserRepository {
  private users: Map<string, User> = new Map();

  constructor(initialData: User[] = []) {
    for (const user of initialData) {
      this.users.set(user.id, user);
    }
  }

  async findById(id: string): Promise<User | null> {
    return this.users.get(id) || null;
  }

  async update(id: string, data: Partial<Pick<User, 'name'>>): Promise<User> {
    const user = this.users.get(id);
    if (!user) throw new Error('user_not_found');
    const updatedUser = { ...user, ...data };
    this.users.set(id, updatedUser);
    return updatedUser;
  }

  async save(user: User): Promise<void> {
    this.users.set(user.id, user);
  }
}
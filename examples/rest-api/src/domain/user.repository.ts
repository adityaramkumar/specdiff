// generated_from: behaviors/users/profile
// spec_hash: 0b617acb52c2f132b799bc16470845b2594558e0726d102a13875aa879178b29
// generated_at: 2026-03-14T21:59:24.902881+00:00
// agent: implementation-agent
import { User } from './user';

export interface UserRepository {
  findById(id: string): Promise<User | null>;
  update(id: string, data: Partial<Pick<User, 'name'>>): Promise<User>;
  save(user: User): Promise<void>;
}
// generated_from: behaviors/auth/login
// spec_hash: 3e8460ea156b262964d71466b05a1aee93705931a00932181862872401776894
// generated_at: 2026-03-14T21:58:57.662741+00:00
// agent: implementation-agent
export interface UserRecord { id: string; email: string; password_hash: string; }
export interface UserStore {
  findByEmail(email: string): Promise<UserRecord | null>;
  save(user: UserRecord): Promise<void>;
}

class InMemoryUserStore implements UserStore {
  private users: Map<string, UserRecord> = new Map();

  async findByEmail(email: string): Promise<UserRecord | null> {
    for (const user of this.users.values()) {
      if (user.email === email) return user;
    }
    return null;
  }

  async save(user: UserRecord): Promise<void> {
    this.users.set(user.id, user);
  }
}

export const userStore: UserStore = new InMemoryUserStore();
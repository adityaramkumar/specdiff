# generated_from: behaviors/auth/login
# spec_hash: 00335c53ca3b6c799e009972b346695606d4fcc3a9ac7f85e4fc5ef7179f7657
# generated_at: 2026-03-10T07:36:18.777372+00:00
# agent: implementation-agent-v0.1

import { UserStore } from './user.store';

export class AuthService {
  private store = new UserStore();

  async authenticate(email: string, password: string) {
    const user = await this.store.findByEmail(email);
    
    if (await this.store.isLocked(email)) {
      throw new Error('account_locked');
    }

    if (!user || user.password !== password) {
      await this.store.recordFailedAttempt(email);
      throw new Error('invalid_credentials');
    }

    return user;
  }
}
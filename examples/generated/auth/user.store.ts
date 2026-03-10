# generated_from: behaviors/auth/login
# spec_hash: 00335c53ca3b6c799e009972b346695606d4fcc3a9ac7f85e4fc5ef7179f7657
# generated_at: 2026-03-10T07:36:18.777372+00:00
# agent: implementation-agent-v0.1

interface Attempt {
  timestamp: number;
}

export class UserStore {
  private failedAttempts: Map<string, Attempt[]> = new Map();

  async findByEmail(email: string) {
    // Mock DB fetch
    return { id: '123', email, password: 'password123' };
  }

  async isLocked(email: string): Promise<boolean> {
    const attempts = this.failedAttempts.get(email) || [];
    const now = Date.now();
    const tenMinutesAgo = now - (10 * 60 * 1000);
    
    const recentAttempts = attempts.filter(a => a.timestamp > tenMinutesAgo);
    
    if (recentAttempts.length >= 5) {
      const lastAttempt = recentAttempts[recentAttempts.length - 1];
      if (now - lastAttempt.timestamp < (30 * 60 * 1000)) {
        return true;
      }
    }
    return false;
  }

  async recordFailedAttempt(email: string) {
    const attempts = this.failedAttempts.get(email) || [];
    attempts.push({ timestamp: Date.now() });
    this.failedAttempts.set(email, attempts);
  }
}
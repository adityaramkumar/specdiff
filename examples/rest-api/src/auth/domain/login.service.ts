// generated_from: behaviors/auth/login
// spec_hash: 00335c53ca3b6c799e009972b346695606d4fcc3a9ac7f85e4fc5ef7179f7657
// generated_at: 2026-03-10T09:00:14.215136+00:00
// agent: implementation-agent
import { UserCredentials, LoginResult } from './auth.types';
import { IUserRepository } from '../infrastructure/user.repository';
import { IPasswordHasher } from '../infrastructure/password.hasher';
import { IJwtProvider } from '../infrastructure/jwt.provider';

export class LoginService {
  constructor(
    private userRepository: IUserRepository,
    private passwordHasher: IPasswordHasher,
    private jwtProvider: IJwtProvider
  ) {}

  async login(credentials: UserCredentials): Promise<LoginResult> {
    const user = await this.userRepository.findByEmail(credentials.email);

    if (!user) throw new Error('invalid_credentials');

    if (user.locked_until && new Date(user.locked_until) > new Date()) {
      throw new Error('account_locked');
    }

    const isValid = await this.passwordHasher.verify(credentials.password, user.password_hash);

    if (!isValid) {
      await this.userRepository.recordFailedAttempt(user.id);
      throw new Error('invalid_credentials');
    }

    const token = this.jwtProvider.sign({ sub: user.id }, { expiresIn: '1h' });
    return { token, redirect: '/dashboard' };
  }
}
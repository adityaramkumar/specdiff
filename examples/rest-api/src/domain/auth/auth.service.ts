// generated_from: contracts/api/users
// spec_hash: 5cf5cc538d1b81c8c474dcd47c648ab4c75be2232eb84c596a9c8849e1842678
// generated_at: 2026-03-10T09:00:06.432869+00:00
// agent: implementation-agent
import { IUserRepository } from '../user/user.repository.interface';

export class AuthService {
  constructor(private userRepository: IUserRepository, private passwordHasher: any, private jwtProvider: any) {}

  async login(email: string, password: string) {
    const user = await this.userRepository.findByEmail(email);
    if (!user) throw new Error('invalid_credentials');
    if (user.locked_until && new Date(user.locked_until) > new Date()) throw new Error('account_locked');
    
    const isValid = await this.passwordHasher.verify(password, user.password_hash);
    if (!isValid) throw new Error('invalid_credentials');

    return { token: this.jwtProvider.sign(user.id), redirect: '/dashboard' };
  }

  async signup(data: { email: string; password: string; name: string }) {
    const existing = await this.userRepository.findByEmail(data.email);
    if (existing) throw new Error('email_already_registered');
    
    const password_hash = await this.passwordHasher.hash(data.password);
    const user = await this.userRepository.create({ email: data.email, password_hash, locked_until: null });
    return { id: user.id, email: user.email };
  }
}
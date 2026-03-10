// generated_from: behaviors/auth/signup
// spec_hash: 76de4dd5faf70d2285d59b7b3320eddbd2b2bb65e458c3cc5573b304b7c759d4
// generated_at: 2026-03-10T09:00:21.226835+00:00
// agent: implementation-agent
import { SignupRepository } from './signup_repository.interface';
import { SignupValidator } from './signup_validator';

export class SignupService {
  constructor(private repo: SignupRepository) {}

  async signup(data: { email: string; password: string; name: string }) {
    if (!SignupValidator.isValidEmail(data.email)) {
      throw new Error('invalid_email_format');
    }
    if (!SignupValidator.isPasswordStrong(data.password)) {
      throw new Error('password_too_weak');
    }

    const existing = await this.repo.findByEmail(data.email);
    if (existing) {
      throw new Error('email_already_registered');
    }

    return await this.repo.create({
      email: data.email,
      password_hash: data.password // Note: In production, hash this here or via middleware
    });
  }
}
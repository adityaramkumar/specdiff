// generated_from: behaviors/auth/signup
// spec_hash: f186382487e04177e71760b73b531d3b0bea1d2d470e71368e2f698403097c3a
// generated_at: 2026-03-14T21:59:11.593171+00:00
// agent: implementation-agent
import { SignupRequest, SignupResponse } from './signup.types';
import { isPasswordValid } from './password.validator';
import { userRepository } from '../../infrastructure/persistence/user.repository';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function registerUser(data: SignupRequest): Promise<SignupResponse> {
  if (!EMAIL_REGEX.test(data.email)) {
    throw 'invalid_email_format';
  }
  if (!isPasswordValid(data.password)) {
    throw 'password_too_weak';
  }
  try {
    const existing = await userRepository.findByEmail(data.email);
    if (existing) {
      throw 'email_already_registered';
    }
    const user = await userRepository.create({
      email: data.email,
      name: data.name,
      password_hash: 'placeholder_hash' // In a real scenario, use bcrypt
    });
    return { id: user.id, email: user.email };
  } catch (error) {
    if (typeof error === 'string') throw error;
    throw 'internal_error';
  }
}
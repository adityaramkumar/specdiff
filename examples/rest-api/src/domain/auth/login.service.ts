// generated_from: behaviors/auth/login
// spec_hash: 3e8460ea156b262964d71466b05a1aee93705931a00932181862872401776894
// generated_at: 2026-03-14T21:58:57.671727+00:00
// agent: implementation-agent
import { userStore } from './user.store';
import { generateToken } from '../../infrastructure/security/jwt.provider';

export interface LoginResponse { token: string; redirect: string; }

export class LoginError extends Error {
  constructor(public code: string, public status: number) {
    super(code);
  }
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const user = await userStore.findByEmail(email);
  
  if (!user || user.password_hash !== password) {
    throw new LoginError('invalid_credentials', 401);
  }

  return {
    token: generateToken({ userId: user.id }),
    redirect: '/dashboard'
  };
}
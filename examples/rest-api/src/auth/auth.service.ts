// generated_from: contracts/api/users
// spec_hash: f40252d816057e05a68d187a6823e059435ed25eb34fc5abde3ceba2491cd49a
// generated_at: 2026-03-14T21:58:45.328223+00:00
// agent: implementation-agent
import { User } from '../types/user';
import { hashPassword, verifyPassword } from './password.utils';
import { v4 as uuidv4 } from 'uuid';

export interface LoginResponse { token: string; redirect: string; }
export interface SignupResponse { id: string; email: string; }

const mockDb: User[] = [];

export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  if (!email.includes('@')) throw new Error('invalid_email_format');
  
  const user = mockDb.find(u => u.email === email);
  if (!user || !(await verifyPassword(password, user.password_hash))) {
    throw new Error('invalid_credentials');
  }

  return { token: 'mock-jwt-token', redirect: '/dashboard' };
}

export async function signupUser(email: string, password: string, name: string): Promise<SignupResponse> {
  if (!email.includes('@')) throw new Error('invalid_email_format');
  if (password.length < 8) throw new Error('password_too_weak');
  if (mockDb.find(u => u.email === email)) throw new Error('email_already_registered');

  const newUser: User = {
    id: uuidv4(),
    email,
    name,
    password_hash: await hashPassword(password),
    created_at: new Date().toISOString()
  };

  mockDb.push(newUser);
  return { id: newUser.id, email: newUser.email };
}
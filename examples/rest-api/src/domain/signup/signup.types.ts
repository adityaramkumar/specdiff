// generated_from: behaviors/auth/signup
// spec_hash: f186382487e04177e71760b73b531d3b0bea1d2d470e71368e2f698403097c3a
// generated_at: 2026-03-14T21:59:11.584566+00:00
// agent: implementation-agent
export interface SignupRequest { email: string; password: string; name: string; }
export interface SignupResponse { id: string; email: string; }
export type SignupError = 'invalid_email_format' | 'password_too_weak' | 'email_already_registered' | 'internal_error';
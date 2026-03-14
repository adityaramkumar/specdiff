// generated_from: behaviors/auth/signup
// spec_hash: f186382487e04177e71760b73b531d3b0bea1d2d470e71368e2f698403097c3a
// generated_at: 2026-03-14T21:59:11.597045+00:00
// agent: implementation-agent
import { Request, Response } from 'express';
import { registerUser } from '../../domain/signup/signup.service';

export async function handleSignup(req: Request, res: Response): Promise<void> {
  try {
    const user = await registerUser(req.body);
    res.status(201).json(user);
  } catch (error) {
    switch (error) {
      case 'invalid_email_format':
      case 'password_too_weak':
        res.status(422).json({ error });
        break;
      case 'email_already_registered':
        res.status(409).json({ error });
        break;
      default:
        res.status(500).json({ error: 'internal_error' });
    }
  }
}
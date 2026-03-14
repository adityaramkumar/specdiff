// generated_from: contracts/api/users
// spec_hash: f40252d816057e05a68d187a6823e059435ed25eb34fc5abde3ceba2491cd49a
// generated_at: 2026-03-14T21:58:45.332468+00:00
// agent: implementation-agent
import { Request, Response } from 'express';
import { loginUser, signupUser } from '../auth/auth.service';

export async function handleLogin(req: Request, res: Response): Promise<void> {
  try {
    const { email, password } = req.body;
    const result = await loginUser(email, password);
    res.status(200).json(result);
  } catch (err: any) {
    if (err.message === 'invalid_email_format') res.status(422).json({ error: 'invalid_email_format' });
    else if (err.message === 'invalid_credentials') res.status(401).json({ error: 'invalid_credentials' });
    else res.status(500).json({ error: 'internal_server_error' });
  }
}

export async function handleSignup(req: Request, res: Response): Promise<void> {
  try {
    const { email, password, name } = req.body;
    const result = await signupUser(email, password, name);
    res.status(201).json(result);
  } catch (err: any) {
    if (err.message === 'invalid_email_format') res.status(422).json({ error: 'invalid_email_format' });
    else if (err.message === 'password_too_weak') res.status(422).json({ error: 'password_too_weak' });
    else if (err.message === 'email_already_registered') res.status(409).json({ error: 'email_already_registered' });
    else res.status(500).json({ error: 'internal_server_error' });
  }
}
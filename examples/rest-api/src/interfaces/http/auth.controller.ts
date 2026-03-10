// generated_from: contracts/api/users
// spec_hash: 5cf5cc538d1b81c8c474dcd47c648ab4c75be2232eb84c596a9c8849e1842678
// generated_at: 2026-03-10T09:00:06.432869+00:00
// agent: implementation-agent
import { Request, Response } from 'express';
import { AuthService } from '../../domain/auth/auth.service';

export class AuthController {
  constructor(private authService: AuthService) {}

  login = async (req: Request, res: Response) => {
    try {
      const result = await this.authService.login(req.body.email, req.body.password);
      res.status(200).json(result);
    } catch (err: any) {
      if (err.message === 'invalid_credentials') res.status(401).json({ error: 'invalid_credentials' });
      else if (err.message === 'account_locked') res.status(403).json({ error: 'account_locked' });
      else res.status(422).json({ error: 'invalid_email_format' });
    }
  };

  signup = async (req: Request, res: Response) => {
    try {
      const result = await this.authService.signup(req.body);
      res.status(201).json(result);
    } catch (err: any) {
      if (err.message === 'email_already_registered') res.status(409).json({ error: 'email_already_registered' });
      else res.status(422).json({ error: err.message === 'password_too_weak' ? 'password_too_weak' : 'invalid_email_format' });
    }
  };
}
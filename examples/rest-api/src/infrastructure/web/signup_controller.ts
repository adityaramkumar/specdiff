// generated_from: behaviors/auth/signup
// spec_hash: 76de4dd5faf70d2285d59b7b3320eddbd2b2bb65e458c3cc5573b304b7c759d4
// generated_at: 2026-03-10T09:00:21.226835+00:00
// agent: implementation-agent
import { Request, Response } from 'express';
import { SignupService } from '../../domain/signup/signup_service';

export class SignupController {
  constructor(private signupService: SignupService) {}

  async handle(req: Request, res: Response) {
    try {
      const result = await this.signupService.signup(req.body);
      res.status(201).json({ id: result.id, email: result.email });
    } catch (err: any) {
      if (err.message === 'invalid_email_format' || err.message === 'password_too_weak') {
        res.status(422).json({ error: err.message });
      } else if (err.message === 'email_already_registered') {
        res.status(409).json({ error: err.message });
      } else {
        res.status(500).json({ error: 'internal_server_error' });
      }
    }
  }
}
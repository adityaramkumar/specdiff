// generated_from: behaviors/auth/login
// spec_hash: 00335c53ca3b6c799e009972b346695606d4fcc3a9ac7f85e4fc5ef7179f7657
// generated_at: 2026-03-10T09:00:14.215136+00:00
// agent: implementation-agent
import { Request, Response } from 'express';
import { LoginService } from '../../domain/login.service';
import { validateEmail } from './login.validator';

export class LoginController {
  constructor(private loginService: LoginService) {}

  handle = async (req: Request, res: Response) => {
    const { email, password } = req.body;

    if (!validateEmail(email)) {
      return res.status(422).json({ error: 'invalid_email_format' });
    }

    try {
      const result = await this.loginService.login({ email, password });
      return res.status(200).json(result);
    } catch (err: any) {
      if (err.message === 'invalid_credentials') {
        return res.status(401).json({ error: 'invalid_credentials' });
      }
      if (err.message === 'account_locked') {
        return res.status(403).json({ error: 'account_locked' });
      }
      return res.status(500).json({ error: 'internal_server_error' });
    }
  };
}
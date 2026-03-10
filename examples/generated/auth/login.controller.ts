# generated_from: behaviors/auth/login
# spec_hash: 00335c53ca3b6c799e009972b346695606d4fcc3a9ac7f85e4fc5ef7179f7657
# generated_at: 2026-03-10T07:36:18.777372+00:00
# agent: implementation-agent-v0.1

import { Request, Response } from 'express';
import jwt from 'jsonwebtoken';
import { AuthService } from './auth.service';

const authService = new AuthService();

export const login = async (req: Request, res: Response) => {
  const { email, password } = req.body;

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!email || !emailRegex.test(email)) {
    return res.status(422).json({ error: 'invalid_email_format' });
  }

  try {
    const user = await authService.authenticate(email, password);

    const token = jwt.sign({ sub: user.id }, process.env.JWT_SECRET || 'secret', { expiresIn: '1h' });
    
    return res.status(200).json({ token, redirect: '/dashboard' });
  } catch (error: any) {
    if (error.message === 'account_locked') {
      return res.status(403).json({ error: 'account_locked' });
    }
    return res.status(401).json({ error: 'invalid_credentials' });
  }
};
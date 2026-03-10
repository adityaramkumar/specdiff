// generated_from: behaviors/auth/login
// spec_hash: 00335c53ca3b6c799e009972b346695606d4fcc3a9ac7f85e4fc5ef7179f7657
// generated_at: 2026-03-10T09:00:14.215136+00:00
// agent: implementation-agent
import { Router } from 'express';
import { LoginController } from './login.controller';

export const authRoutes = (loginController: LoginController) => {
  const router = Router();
  router.post('/login', loginController.handle);
  return router;
};
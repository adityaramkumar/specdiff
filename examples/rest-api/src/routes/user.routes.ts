// generated_from: behaviors/users/profile
// spec_hash: d1f76ac9b12b1560185010f04ecae9a79ca4e17e78accdbabc8ee582b60bbd58
// generated_at: 2026-03-10T09:00:31.838622+00:00
// agent: implementation-agent
import { Router } from 'express';
import { UserController } from '../controllers/user.controller';
import { authMiddleware } from '../middleware/auth.middleware';

export const createUserRoutes = (controller: UserController) => {
  const router = Router();
  router.get('/:id', authMiddleware, controller.getProfile);
  router.put('/:id', authMiddleware, controller.updateProfile);
  return router;
};
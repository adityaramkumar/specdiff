// generated_from: behaviors/users/profile
// spec_hash: d1f76ac9b12b1560185010f04ecae9a79ca4e17e78accdbabc8ee582b60bbd58
// generated_at: 2026-03-10T09:00:31.838622+00:00
// agent: implementation-agent
import { Request, Response } from 'express';
import { UserService } from '../services/user.service';

export class UserController {
  constructor(private userService: UserService) {}

  getProfile = async (req: Request, res: Response) => {
    try {
      const user = await this.userService.getProfile(req.params.id, (req as any).user.id);
      return res.status(200).json(user);
    } catch (err: any) {
      return res.status(err.status || 500).json({ error: err.error || 'internal_server_error' });
    }
  };

  updateProfile = async (req: Request, res: Response) => {
    try {
      const user = await this.userService.updateProfile(req.params.id, (req as any).user.id, req.body.name);
      return res.status(200).json(user);
    } catch (err: any) {
      return res.status(err.status || 500).json({ error: err.error || 'internal_server_error' });
    }
  };
}
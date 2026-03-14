// generated_from: behaviors/users/profile
// spec_hash: 0b617acb52c2f132b799bc16470845b2594558e0726d102a13875aa879178b29
// generated_at: 2026-03-14T21:59:24.910323+00:00
// agent: implementation-agent
import { Request, Response } from 'express';
import { UserRepository } from '../../domain/user.repository';
import { getUserProfile } from '../../application/get-user.service';
import { updateUserName } from '../../application/update-user.service';

export class UserController {
  constructor(private repository: UserRepository) {}

  async getUser(req: Request, res: Response): Promise<void> {
    try {
      const profile = await getUserProfile(req.params.id, this.repository);
      res.status(200).json(profile);
    } catch (err: any) {
      if (err.message === 'user_not_found') {
        res.status(404).json({ error: 'user_not_found' });
      } else {
        res.status(500).json({ error: 'internal_error' });
      }
    }
  }

  async updateUser(req: Request, res: Response): Promise<void> {
    try {
      const profile = await updateUserName(req.params.id, req.body.name, this.repository);
      res.status(200).json(profile);
    } catch (err: any) {
      if (err.message === 'name_required' || err.message === 'name_too_long') {
        res.status(422).json({ error: err.message });
      } else if (err.message === 'user_not_found') {
        res.status(404).json({ error: 'user_not_found' });
      } else {
        res.status(500).json({ error: 'internal_error' });
      }
    }
  }
}
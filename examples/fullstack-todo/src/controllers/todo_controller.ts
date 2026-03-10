// generated_from: behaviors/backend/crud
// spec_hash: 8b55d2dbbc650b7f723f46ef764d5ac1fcd143b6e5dd35a8812c4a3958f4c506
// generated_at: 2026-03-10T09:05:09.387482+00:00
// agent: implementation-agent
import { Request, Response } from 'express';
import { todoService } from '../services/todo_service';

export const todoController = {
  create: (req: Request, res: Response) => {
    try {
      const todo = todoService.create(req.body.title);
      res.status(201).json(todo);
    } catch (e: any) {
      res.status(422).json({ error: e.message });
    }
  },
  list: (req: Request, res: Response) => {
    const completed = req.query.completed ? req.query.completed === 'true' : undefined;
    res.json(todoService.list(completed));
  },
  update: (req: Request, res: Response) => {
    try {
      const todo = todoService.update(req.params.id, req.body);
      res.status(200).json(todo);
    } catch (e: any) {
      if (e.message === 'todo_not_found') res.status(404).json({ error: e.message });
      else res.status(422).json({ error: e.message });
    }
  },
  delete: (req: Request, res: Response) => {
    try {
      todoService.delete(req.params.id);
      res.status(204).send();
    } catch (e: any) {
      res.status(404).json({ error: e.message });
    }
  }
};
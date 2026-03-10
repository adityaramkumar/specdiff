// generated_from: contracts/api/todos
// spec_hash: 0edfd134984717f0c86b423c6e3a9c4dd47d659c8d65c91c3346104402c3e1bb
// generated_at: 2026-03-10T09:05:02.108375+00:00
// agent: implementation-agent
import { Request, Response } from 'express';
import { TodoService } from '../../application/todo.service';
import { validateTitle } from '../../domain/todo';

export class TodoController {
  constructor(private service: TodoService) {}

  getAll = async (req: Request, res: Response) => {
    const completed = req.query.completed === 'true' ? true : req.query.completed === 'false' ? false : undefined;
    const result = await this.service.getAll(completed);
    res.json(result);
  };

  create = async (req: Request, res: Response) => {
    const { title } = req.body;
    const validation = validateTitle(title);
    if (validation === 'required') return res.status(422).json({ error: 'title_required' });
    if (validation === 'too_long') return res.status(422).json({ error: 'title_too_long' });
    const todo = await this.service.create(title);
    res.status(201).json(todo);
  };

  update = async (req: Request, res: Response) => {
    const { id } = req.params;
    const { title } = req.body;
    if (title && validateTitle(title) === 'too_long') return res.status(422).json({ error: 'title_too_long' });
    const todo = await this.service.update(id, req.body);
    if (!todo) return res.status(404).json({ error: 'todo_not_found' });
    res.json(todo);
  };

  delete = async (req: Request, res: Response) => {
    const success = await this.service.delete(req.params.id);
    if (!success) return res.status(404).json({ error: 'todo_not_found' });
    res.status(204).send();
  };
}
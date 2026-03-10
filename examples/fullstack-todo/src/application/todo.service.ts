// generated_from: contracts/api/todos
// spec_hash: 0edfd134984717f0c86b423c6e3a9c4dd47d659c8d65c91c3346104402c3e1bb
// generated_at: 2026-03-10T09:05:02.108375+00:00
// agent: implementation-agent
import { Todo } from '../domain/todo';
import { TodoRepository } from '../domain/todo.repository';

export class TodoService {
  constructor(private repository: TodoRepository) {}

  async getAll(completed?: boolean) {
    return this.repository.findAll(completed);
  }

  async create(title: string) {
    return this.repository.create(title);
  }

  async update(id: string, data: { title?: string; completed?: boolean }) {
    return this.repository.update(id, data);
  }

  async delete(id: string) {
    return this.repository.delete(id);
  }
}
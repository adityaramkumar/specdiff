// generated_from: contracts/api/todos
// spec_hash: 0edfd134984717f0c86b423c6e3a9c4dd47d659c8d65c91c3346104402c3e1bb
// generated_at: 2026-03-10T09:05:02.108375+00:00
// agent: implementation-agent
import { Todo } from './todo';

export interface TodoRepository {
  findAll(completed?: boolean): Promise<{ todos: Todo[]; count: number }>;
  findById(id: string): Promise<Todo | null>;
  create(title: string): Promise<Todo>;
  update(id: string, data: Partial<Pick<Todo, 'title' | 'completed'>>): Promise<Todo | null>;
  delete(id: string): Promise<boolean>;
}
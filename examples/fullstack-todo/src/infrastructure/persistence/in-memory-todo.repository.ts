// generated_from: contracts/api/todos
// spec_hash: 0edfd134984717f0c86b423c6e3a9c4dd47d659c8d65c91c3346104402c3e1bb
// generated_at: 2026-03-10T09:05:02.108375+00:00
// agent: implementation-agent
import { Todo } from '../../domain/todo';
import { TodoRepository } from '../../domain/todo.repository';

export class InMemoryTodoRepository implements TodoRepository {
  private todos: Todo[] = [];

  async findAll(completed?: boolean) {
    let filtered = this.todos;
    if (completed !== undefined) {
      filtered = filtered.filter(t => t.completed === completed);
    }
    return { todos: filtered, count: filtered.length };
  }

  async findById(id: string) {
    return this.todos.find(t => t.id === id) || null;
  }

  async create(title: string) {
    const todo: Todo = {
      id: Math.random().toString(36).substring(7),
      title,
      completed: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    this.todos.push(todo);
    return todo;
  }

  async update(id: string, data: Partial<Pick<Todo, 'title' | 'completed'>>) {
    const index = this.todos.findIndex(t => t.id === id);
    if (index === -1) return null;
    this.todos[index] = { ...this.todos[index], ...data, updated_at: new Date().toISOString() };
    return this.todos[index];
  }

  async delete(id: string) {
    const index = this.todos.findIndex(t => t.id === id);
    if (index === -1) return false;
    this.todos.splice(index, 1);
    return true;
  }
}
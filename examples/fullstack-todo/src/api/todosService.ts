// generated_from: behaviors/frontend/todo-list
// spec_hash: ae9098db446b8b3733f3f183a371cf61070932b2ec6b570d5436a6dc228239f6
// generated_at: 2026-03-10T09:05:26.983546+00:00
// agent: implementation-agent
import { Todo } from '../types/todo';

export const todosService = {
  getAll: async (): Promise<{ todos: Todo[]; count: number }> => {
    const res = await fetch('/api/todos');
    if (!res.ok) throw new Error('Failed to fetch');
    return res.json();
  },
  create: async (title: string): Promise<Todo> => {
    const res = await fetch('/api/todos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    if (!res.ok) throw await res.json();
    return res.json();
  },
  update: async (id: string, updates: { completed?: boolean }): Promise<Todo> => {
    const res = await fetch(`/api/todos/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw await res.json();
    return res.json();
  },
  delete: async (id: string): Promise<void> => {
    const res = await fetch(`/api/todos/${id}`, { method: 'DELETE' });
    if (!res.ok) throw await res.json();
  },
};
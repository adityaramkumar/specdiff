// generated_from: behaviors/backend/crud
// spec_hash: 8b55d2dbbc650b7f723f46ef764d5ac1fcd143b6e5dd35a8812c4a3958f4c506
// generated_at: 2026-03-10T09:05:09.387482+00:00
// agent: implementation-agent
import { Todo } from '../models/todo';

const todos: Todo[] = [];

export const todoRepository = {
  findAll: () => [...todos],
  save: (todo: Todo) => {
    const index = todos.findIndex((t) => t.id === todo.id);
    if (index === -1) {
      todos.push(todo);
    } else {
      todos[index] = todo;
    }
    return todo;
  },
  findById: (id: string) => todos.find((t) => t.id === id),
  delete: (id: string) => {
    const index = todos.findIndex((t) => t.id === id);
    if (index !== -1) {
      todos.splice(index, 1);
      return true;
    }
    return false;
  }
};
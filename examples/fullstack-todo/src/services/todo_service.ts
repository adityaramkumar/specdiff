// generated_from: behaviors/backend/crud
// spec_hash: 8b55d2dbbc650b7f723f46ef764d5ac1fcd143b6e5dd35a8812c4a3958f4c506
// generated_at: 2026-03-10T09:05:09.387482+00:00
// agent: implementation-agent
import { v4 as uuidv4 } from 'uuid';
import { Todo } from '../models/todo';
import { todoRepository } from '../repositories/todo_repository';

export const todoService = {
  create: (title: string): Todo => {
    if (!title || title.trim().length === 0) throw new Error('title_required');
    if (title.length > 200) throw new Error('title_too_long');

    const now = new Date().toISOString();
    const todo: Todo = {
      id: uuidv4(),
      title,
      completed: false,
      created_at: now,
      updated_at: now
    };
    return todoRepository.save(todo);
  },
  list: (completed?: boolean): { todos: Todo[], count: number } => {
    let todos = todoRepository.findAll();
    if (completed !== undefined) {
      todos = todos.filter(t => t.completed === completed);
    }
    todos.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    return { todos, count: todos.length };
  },
  update: (id: string, updates: { title?: string, completed?: boolean }): Todo => {
    const todo = todoRepository.findById(id);
    if (!todo) throw new Error('todo_not_found');
    if (updates.title && updates.title.length > 200) throw new Error('title_too_long');

    const updatedTodo = { 
        ...todo, 
        ...updates, 
        updated_at: new Date().toISOString() 
    };
    return todoRepository.save(updatedTodo);
  },
  delete: (id: string): void => {
    if (!todoRepository.delete(id)) throw new Error('todo_not_found');
  }
};
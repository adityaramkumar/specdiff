// generated_from: behaviors/frontend/todo-list
// spec_hash: ae9098db446b8b3733f3f183a371cf61070932b2ec6b570d5436a6dc228239f6
// generated_at: 2026-03-10T09:05:26.983546+00:00
// agent: implementation-agent
import { useState, useEffect } from 'react';
import { Todo } from '../types/todo';
import { todosService } from '../api/todosService';

export const useTodos = () => {
  const [todos, setTodos] = useState<Todo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTodos = async () => {
    setLoading(true);
    setError(null);
    try {
      const { todos } = await todosService.getAll();
      setTodos(todos);
    } catch { setError('Failed to load todos. Try again.'); } 
    finally { setLoading(false); }
  };

  useEffect(() => { fetchTodos(); }, []);

  const addTodo = async (title: string) => {
    try {
      const newTodo = await todosService.create(title);
      setTodos([newTodo, ...todos]);
    } catch { throw new Error('Failed to add todo'); }
  };

  const toggleTodo = async (id: string) => {
    const originalTodos = [...todos];
    const todo = todos.find(t => t.id === id);
    if (!todo) return;

    setTodos(todos.map(t => t.id === id ? { ...t, completed: !t.completed } : t));
    try {
      await todosService.update(id, { completed: !todo.completed });
    } catch { 
      setTodos(originalTodos);
      alert('Failed to update todo');
    }
  };

  const deleteTodo = async (id: string) => {
    const originalTodos = [...todos];
    setTodos(todos.filter(t => t.id !== id));
    try {
      await todosService.delete(id);
    } catch { 
      setTodos(originalTodos);
      alert('Failed to delete todo');
    }
  };

  return { todos, loading, error, fetchTodos, addTodo, toggleTodo, deleteTodo };
};
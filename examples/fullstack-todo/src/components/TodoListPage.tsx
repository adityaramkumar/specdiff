// generated_from: behaviors/frontend/todo-list
// spec_hash: ae9098db446b8b3733f3f183a371cf61070932b2ec6b570d5436a6dc228239f6
// generated_at: 2026-03-10T09:05:26.983546+00:00
// agent: implementation-agent
import React, { useState } from 'react';
import { useTodos } from '../hooks/useTodos';
import { TodoList } from './TodoList';
import { AddTodoForm } from './AddTodoForm';
import { TodoFilter } from './TodoFilter';

export const TodoListPage = () => {
  const { todos, loading, error, fetchTodos, addTodo, toggleTodo, deleteTodo } = useTodos();
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all');
  const [addError, setAddError] = useState<string | null>(null);

  const filteredTodos = todos.filter(t => 
    filter === 'all' ? true : filter === 'active' ? !t.completed : t.completed
  );

  const handleAdd = async (title: string) => {
    setAddError(null);
    try { await addTodo(title); } 
    catch { setAddError('Failed to add todo'); }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>{error} <button onClick={fetchTodos}>Retry</button></div>;

  return (
    <div>
      <TodoFilter filter={filter} onChange={setFilter} />
      <AddTodoForm onAdd={handleAdd} />
      {addError && <p>{addError}</p>}
      <TodoList todos={filteredTodos} onToggle={toggleTodo} onDelete={deleteTodo} />
    </div>
  );
};
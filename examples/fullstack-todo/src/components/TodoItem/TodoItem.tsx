// generated_from: contracts/ui/components
// spec_hash: 12e101232da0b497b76851531c4e21348b66f81335de4f73ff49135f4ce465f3
// generated_at: 2026-03-10T09:05:17.954478+00:00
// agent: implementation-agent
import React from 'react';
import { Todo } from '../../types/todo';

interface TodoItemProps {
  todo: Todo;
  onToggle: (id: string) => void;
  onDelete: (id: string) => void;
}

export const TodoItem: React.FC<TodoItemProps> = ({ todo, onToggle, onDelete }) => (
  <li>
    <input
      type="checkbox"
      checked={todo.completed}
      onChange={() => onToggle(todo.id)}
    />
    <span style={{ textDecoration: todo.completed ? 'line-through' : 'none' }}>
      {todo.title}
    </span>
    <button onClick={() => onDelete(todo.id)}>Delete</button>
  </li>
);
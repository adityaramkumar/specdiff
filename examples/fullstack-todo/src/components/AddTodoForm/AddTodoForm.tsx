// generated_from: contracts/ui/components
// spec_hash: 12e101232da0b497b76851531c4e21348b66f81335de4f73ff49135f4ce465f3
// generated_at: 2026-03-10T09:05:17.954478+00:00
// agent: implementation-agent
import React, { useState } from 'react';

interface AddTodoFormProps {
  onAdd: (title: string) => void;
}

export const AddTodoForm: React.FC<AddTodoFormProps> = ({ onAdd }) => {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (trimmed) {
      onAdd(trimmed);
      setInput('');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        maxLength={200}
      />
      <button type="submit" disabled={!input.trim()}>
        Add Todo
      </button>
    </form>
  );
};
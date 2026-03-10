// generated_from: contracts/api/todos
// spec_hash: 0edfd134984717f0c86b423c6e3a9c4dd47d659c8d65c91c3346104402c3e1bb
// generated_at: 2026-03-10T09:05:02.108375+00:00
// agent: implementation-agent
export interface Todo {
  id: string;
  title: string;
  completed: boolean;
  created_at: string;
  updated_at: string;
}

export const validateTitle = (title: string): 'too_long' | 'required' | null => {
  if (!title || title.trim().length === 0) return 'required';
  if (title.length > 200) return 'too_long';
  return null;
};
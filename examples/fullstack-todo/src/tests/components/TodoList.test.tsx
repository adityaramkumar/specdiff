// generated_from: contracts/ui/components
// spec_hash: 12e101232da0b497b76851531c4e21348b66f81335de4f73ff49135f4ce465f3
// generated_at: 2026-03-10T09:05:17.962011+00:00
// agent: testing-agent
import { render, screen } from '@testing-library/react';
import { TodoList } from '../../components/TodoList/TodoList';

describe('TodoList Component', () => {
  test('renders empty state message when list is empty', () => {
    render(<TodoList todos={[]} onToggle={() => {}} onDelete={() => {}} />);
    expect(screen.getByText(/No todos yet/i)).toBeInTheDocument();
  });

  test('renders TodoItem components for each todo', () => {
    const todos = [
      { id: '1', title: 'One', completed: false, created_at: '', updated_at: '' },
      { id: '2', title: 'Two', completed: true, created_at: '', updated_at: '' }
    ];
    render(<TodoList todos={todos} onToggle={() => {}} onDelete={() => {}} />);
    expect(screen.getAllByRole('checkbox')).toHaveLength(2);
  });
});
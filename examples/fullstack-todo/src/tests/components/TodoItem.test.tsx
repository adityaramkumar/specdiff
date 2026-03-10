// generated_from: contracts/ui/components
// spec_hash: 12e101232da0b497b76851531c4e21348b66f81335de4f73ff49135f4ce465f3
// generated_at: 2026-03-10T09:05:17.962011+00:00
// agent: testing-agent
import { render, screen, fireEvent } from '@testing-library/react';
import { TodoItem } from '../../components/TodoItem/TodoItem';

describe('TodoItem Component', () => {
  const mockTodo = { id: '1', title: 'Test Todo', completed: false, created_at: '', updated_at: '' };

  test('renders checkbox, title, and delete button', () => {
    render(<TodoItem todo={mockTodo} onToggle={() => {}} onDelete={() => {}} />);
    expect(screen.getByRole('checkbox')).toBeInTheDocument();
    expect(screen.getByText('Test Todo')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
  });

  test('checkbox reflects completion status', () => {
    const { rerender } = render(<TodoItem todo={{...mockTodo, completed: true}} onToggle={() => {}} onDelete={() => {}} />);
    expect(screen.getByRole('checkbox')).toBeChecked();
  });

  test('calls onToggle with correct id on checkbox click', () => {
    const onToggle = jest.fn();
    render(<TodoItem todo={mockTodo} onToggle={onToggle} onDelete={() => {}} />);
    fireEvent.click(screen.getByRole('checkbox'));
    expect(onToggle).toHaveBeenCalledWith('1');
  });

  test('calls onDelete with correct id on button click', () => {
    const onDelete = jest.fn();
    render(<TodoItem todo={mockTodo} onToggle={() => {}} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole('button', { name: /delete/i }));
    expect(onDelete).toHaveBeenCalledWith('1');
  });

  test('renders title with strikethrough when completed', () => {
    const { container } = render(<TodoItem todo={{...mockTodo, completed: true}} onToggle={() => {}} onDelete={() => {}} />);
    expect(container.querySelector('[style*="text-decoration"]')).toBeInTheDocument();
  });
});
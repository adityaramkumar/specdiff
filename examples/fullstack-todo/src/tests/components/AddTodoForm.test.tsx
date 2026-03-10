// generated_from: contracts/ui/components
// spec_hash: 12e101232da0b497b76851531c4e21348b66f81335de4f73ff49135f4ce465f3
// generated_at: 2026-03-10T09:05:17.962011+00:00
// agent: testing-agent
import { render, screen, fireEvent } from '@testing-library/react';
import { AddTodoForm } from '../../components/AddTodoForm/AddTodoForm';

describe('AddTodoForm Component', () => {
  test('enforces max length 200 on input', () => {
    render(<AddTodoForm onAdd={() => {}} />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('maxLength', '200');
  });

  test('disables submit button when input is empty or whitespace', () => {
    render(<AddTodoForm onAdd={() => {}} />);
    const button = screen.getByRole('button', { name: /add/i });
    expect(button).toBeDisabled();
    
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '   ' } });
    expect(button).toBeDisabled();
  });

  test('calls onAdd with trimmed input and clears field on submit', () => {
    const onAdd = jest.fn();
    render(<AddTodoForm onAdd={onAdd} />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: '  New Todo  ' } });
    fireEvent.click(screen.getByRole('button', { name: /add/i }));
    expect(onAdd).toHaveBeenCalledWith('New Todo');
    expect(input).toHaveValue('');
  });
});
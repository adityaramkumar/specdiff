// generated_from: behaviors/frontend/todo-list
// spec_hash: ae9098db446b8b3733f3f183a371cf61070932b2ec6b570d5436a6dc228239f6
// generated_at: 2026-03-10T09:05:26.989923+00:00
// agent: testing-agent
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { TodoListPage } from '../../components/TodoListPage';
import * as api from '../../api/todosService';

jest.mock('../../api/todosService');

describe('TodoListPage Integration', () => {
  beforeEach(() => jest.clearAllMocks());

  test('should display loading state then list todos on mount', async () => {
    (api.fetchTodos as jest.Mock).mockResolvedValue({ todos: [{ id: '1', title: 'Test', completed: false }], count: 1 });
    render(<TodoListPage />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('Test')).toBeInTheDocument());
  });

  test('should show error and retry button when fetch fails', async () => {
    (api.fetchTodos as jest.Mock).mockRejectedValue(new Error());
    render(<TodoListPage />);
    await waitFor(() => expect(screen.getByText('Failed to load todos. Try again.')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  test('should add a new todo and prepend it', async () => {
    (api.fetchTodos as jest.Mock).mockResolvedValue({ todos: [], count: 0 });
    (api.createTodo as jest.Mock).mockResolvedValue({ id: '2', title: 'New', completed: false });
    render(<TodoListPage />);
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'New' } });
    fireEvent.click(screen.getByRole('button', { name: /add/i }));
    await waitFor(() => expect(screen.getByText('New')).toBeInTheDocument());
  });

  test('should show inline error when adding fails', async () => {
    (api.fetchTodos as jest.Mock).mockResolvedValue({ todos: [], count: 0 });
    (api.createTodo as jest.Mock).mockRejectedValue(new Error());
    render(<TodoListPage />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'New' } });
    fireEvent.click(screen.getByRole('button', { name: /add/i }));
    await waitFor(() => expect(screen.getByText('Failed to add todo')).toBeInTheDocument());
  });

  test('should optimistically toggle completion', async () => {
    (api.fetchTodos as jest.Mock).mockResolvedValue({ todos: [{ id: '1', title: 'T', completed: false }], count: 1 });
    (api.updateTodo as jest.Mock).mockResolvedValue({ id: '1', title: 'T', completed: true });
    render(<TodoListPage />);
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();
    await waitFor(() => expect(api.updateTodo).toHaveBeenCalledWith('1', { completed: true }));
  });

  test('should delete todo after confirmation', async () => {
    (api.fetchTodos as jest.Mock).mockResolvedValue({ todos: [{ id: '1', title: 'T', completed: false }], count: 1 });
    (api.deleteTodo as jest.Mock).mockResolvedValue({});
    render(<TodoListPage />);
    fireEvent.click(screen.getByRole('button', { name: /delete/i }));
    fireEvent.click(screen.getByText('Delete'));
    await waitFor(() => expect(screen.queryByText('T')).not.toBeInTheDocument());
  });

  test('should filter todos client-side', async () => {
    (api.fetchTodos as jest.Mock).mockResolvedValue({
      todos: [
        { id: '1', title: 'Active', completed: false },
        { id: '2', title: 'Done', completed: true }
      ],
      count: 2
    });
    render(<TodoListPage />);
    fireEvent.click(screen.getByRole('button', { name: /active/i }));
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.queryByText('Done')).not.toBeInTheDocument();
  });
});
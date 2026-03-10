// generated_from: contracts/ui/components
// spec_hash: 12e101232da0b497b76851531c4e21348b66f81335de4f73ff49135f4ce465f3
// generated_at: 2026-03-10T09:05:17.962011+00:00
// agent: testing-agent
import { render, screen } from '@testing-library/react';
import { TodoFilter } from '../../components/TodoFilter/TodoFilter';

describe('TodoFilter Component', () => {
  test('renders all, active, and completed buttons', () => {
    render(<TodoFilter filter="all" onChange={() => {}} />);
    expect(screen.getByRole('button', { name: /all/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /active/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /completed/i })).toBeInTheDocument();
  });

  test('applies distinct visual style to active filter', () => {
    const { rerender } = render(<TodoFilter filter="active" onChange={() => {}} />);
    const activeButton = screen.getByRole('button', { name: /active/i });
    expect(activeButton).toHaveClass('active'); // Implementation detail via class as proxy for spec "distinct style"
  });
});
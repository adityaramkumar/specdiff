// generated_from: contracts/ui/components
// spec_hash: 12e101232da0b497b76851531c4e21348b66f81335de4f73ff49135f4ce465f3
// generated_at: 2026-03-10T09:05:17.954478+00:00
// agent: implementation-agent
import React from 'react';

type FilterType = 'all' | 'active' | 'completed';

interface TodoFilterProps {
  filter: FilterType;
  onChange: (filter: FilterType) => void;
}

export const TodoFilter: React.FC<TodoFilterProps> = ({ filter, onChange }) => {
  const filters: FilterType[] = ['all', 'active', 'completed'];

  return (
    <div>
      {filters.map((f) => (
        <button
          key={f}
          onClick={() => onChange(f)}
          style={{ fontWeight: filter === f ? 'bold' : 'normal' }}
        >
          {f.charAt(0).toUpperCase() + f.slice(1)}
        </button>
      ))}
    </div>
  );
};
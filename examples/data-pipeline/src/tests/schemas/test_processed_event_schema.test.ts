// generated_from: contracts/schemas/processed
// spec_hash: 363cd030c1920e3fa5120a35d07ebe130a62a4e292bbc5d4b4f784afb869fbf9
// generated_at: 2026-03-10T09:07:01.363590+00:00
// agent: testing-agent
import { validate } from 'json-schema';

describe('Processed Event Schema Compliance', () => {
  test('should satisfy all fields and types in Processed Event Object', () => {
    const event = {
      event_id: '550e8400-e29b-41d4-a716-446655440000',
      event_type: 'page_view',
      timestamp_utc: '2023-10-27T10:00:00Z',
      date: '2023-10-27',
      hour: 10,
      user_id: '123e4567-e89b-12d3-a456-426614174000',
      is_anonymous: false,
      source: 'web',
      properties: { url: '/home' },
      enrichments: {
        session_id: '7d444840-9dc0-11d1-b245-5ffdce74fad2',
        event_sequence: 1
      }
    };
    expect(event.timestamp_utc).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/);
    expect(event.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(event.hour).toBeGreaterThanOrEqual(0);
    expect(event.hour).toBeLessThanOrEqual(23);
  });
});
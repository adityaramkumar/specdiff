// generated_from: contracts/schemas/raw-events
// spec_hash: 6eced18bceb8e4b00bcc2656f2b50decf0cd0afdd960b5bf4d162a70a2e71825
// generated_at: 2026-03-10T09:06:52.949708+00:00
// agent: testing-agent
import { validateEvent } from '../validation/event_validator';

describe('Raw Events Schema Validation', () => {
  test('accepts valid event with all fields', () => {
    const event = {
      event_id: '550e8400-e29b-41d4-a716-446655440000',
      event_type: 'page_view',
      timestamp: '2023-10-27T10:00:00Z',
      user_id: '7b2a3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d',
      properties: { url: '/home' },
      source: 'web'
    };
    expect(validateEvent(event)).toBe(true);
  });

  test('accepts valid event with null user_id (anonymous)', () => {
    const event = {
      event_id: '550e8400-e29b-41d4-a716-446655440000',
      event_type: 'click',
      timestamp: '2023-10-27T10:00:00+02:00',
      user_id: null,
      properties: { button_id: 'submit' },
      source: 'mobile'
    };
    expect(validateEvent(event)).toBe(true);
  });

  test('rejects invalid UUID format for event_id', () => {
    const event = { event_id: 'invalid-uuid', event_type: 'purchase', timestamp: '2023-10-27T10:00:00Z', user_id: null, properties: {}, source: 'api' };
    expect(validateEvent(event)).toBe(false);
  });

  test('rejects unsupported event_type', () => {
    const event = { event_id: '550e8400-e29b-41d4-a716-446655440000', event_type: 'invalid_type', timestamp: '2023-10-27T10:00:00Z', user_id: null, properties: {}, source: 'web' };
    expect(validateEvent(event)).toBe(false);
  });

  test('rejects malformed timestamp', () => {
    const event = { event_id: '550e8400-e29b-41d4-a716-446655440000', event_type: 'purchase', timestamp: '2023-10-27', user_id: null, properties: {}, source: 'web' };
    expect(validateEvent(event)).toBe(false);
  });

  test('rejects non-object properties', () => {
    const event = { event_id: '550e8400-e29b-41d4-a716-446655440000', event_type: 'signup', timestamp: '2023-10-27T10:00:00Z', user_id: null, properties: [1, 2, 3], source: 'web' };
    expect(validateEvent(event)).toBe(false);
  });
});
// generated_from: contracts/schemas/processed
// spec_hash: 363cd030c1920e3fa5120a35d07ebe130a62a4e292bbc5d4b4f784afb869fbf9
// generated_at: 2026-03-10T09:07:01.363590+00:00
// agent: testing-agent
describe('Session Assignment Logic', () => {
  test('should group events within 30 minutes under same user as one session', () => {
    const event1 = { user_id: 'u1', timestamp_utc: '2023-10-27T10:00:00Z' };
    const event2 = { user_id: 'u1', timestamp_utc: '2023-10-27T10:25:00Z' };
    const session1 = assignSession(event1);
    const session2 = assignSession(event2);
    expect(session1.enrichments.session_id).toBe(session2.enrichments.session_id);
  });

  test('should create new session after 30 minute gap', () => {
    const event1 = { user_id: 'u1', timestamp_utc: '2023-10-27T10:00:00Z' };
    const event2 = { user_id: 'u1', timestamp_utc: '2023-10-27T10:31:00Z' };
    const session1 = assignSession(event1);
    const session2 = assignSession(event2);
    expect(session1.enrichments.session_id).not.toBe(session2.enrichments.session_id);
  });

  test('should assign unique session to each anonymous event', () => {
    const event1 = { user_id: 'anonymous', timestamp_utc: '2023-10-27T10:00:00Z', is_anonymous: true };
    const event2 = { user_id: 'anonymous', timestamp_utc: '2023-10-27T10:01:00Z', is_anonymous: true };
    const session1 = assignSession(event1);
    const session2 = assignSession(event2);
    expect(session1.enrichments.session_id).not.toBe(session2.enrichments.session_id);
  });
});
// generated_from: behaviors/transform
// spec_hash: 0c693b22255ee8ba03d47bf5d7d244de4eb44cb5bf9c27d0585f3b66550a2eca
// generated_at: 2026-03-10T09:07:27.855105+00:00
// agent: testing-agent
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

describe('pipeline transform happy path', () => {
  it('should transform events and output summary', () => {
    const staging = 'test_data/staging';
    const output = 'test_data/output';
    
    // Setup dummy valid/events.ndjson
    fs.mkdirSync(path.join(staging, 'valid'), { recursive: true });
    const event = JSON.stringify({
      event_id: '550e8400-e29b-41d4-a716-446655440000',
      event_type: 'page_view',
      timestamp: '2023-10-27T10:00:00Z',
      user_id: 'a3d90610-1234-4567-8901-234567890123',
      properties: {},
      source: 'web'
    });
    fs.writeFileSync(path.join(staging, 'valid/events.ndjson'), event);

    const stdout = execSync(`pipeline transform ${staging} --output ${output}`).toString();
    
    expect(stdout).toContain('Transformed 1 events, 1 sessions identified');
    
    const result = JSON.parse(fs.readFileSync(path.join(output, 'events.ndjson'), 'utf-8'));
    expect(result.timestamp_utc).toBe('2023-10-27T10:00:00.000Z');
    expect(result.date).toBe('2023-10-27');
    expect(result.hour).toBe(10);
    expect(result.enrichments.session_id).toBeDefined();
    expect(result.enrichments.event_sequence).toBe(1);
  });
});
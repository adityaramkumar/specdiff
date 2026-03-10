// generated_from: contracts/schemas/raw-events
// spec_hash: 6eced18bceb8e4b00bcc2656f2b50decf0cd0afdd960b5bf4d162a70a2e71825
// generated_at: 2026-03-10T09:06:52.949708+00:00
// agent: testing-agent
import { processNDJSON } from '../processing/stream_processor';
import fs from 'fs';

describe('NDJSON Stream Processing', () => {
  test('routes valid events and writes invalid events to dead-letter file', async () => {
    const ndjson = '{"event_id":"550e8400-e29b-41d4-a716-446655440000","event_type":"page_view","timestamp":"2023-10-27T10:00:00Z","user_id":null,"properties":{},"source":"web"}\n{"event_id":"invalid"}';
    
    const results = await processNDJSON(ndjson);
    
    expect(results.processedCount).toBe(1);
    expect(results.deadLetterCount).toBe(1);
    expect(fs.existsSync('dead_letter.jsonl')).toBe(true);
  });

  test('enforces 64KB size limit per line', async () => {
    const largeLine = '{"event_id":"' + 'a'.repeat(70000) + '"}';
    const results = await processNDJSON(largeLine);
    
    expect(results.deadLetterCount).toBe(1);
  });

  test('handles zero events', async () => {
    const results = await processNDJSON('');
    expect(results.processedCount).toBe(0);
  });
});
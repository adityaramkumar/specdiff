// generated_from: contracts/schemas/processed
// spec_hash: 363cd030c1920e3fa5120a35d07ebe130a62a4e292bbc5d4b4f784afb869fbf9
// generated_at: 2026-03-10T09:07:01.363590+00:00
// agent: testing-agent
import { getEventsByDate } from '../infrastructure/storage/file_partitioner';

describe('Event Storage Partitioning', () => {
  test('should partition events by date directory', async () => {
    // Verify output/{date}/events.ndjson structure
    const result = await processor.process(eventList);
    expect(result.paths).toContain('2023-10-27/events.ndjson');
  });

  test('should enforce 256MB file size limit and split files', async () => {
    const largeEventStream = generateEvents(300 * 1024 * 1024); // > 256MB
    const files = await processor.process(largeEventStream);
    expect(files['2023-10-27'].length).toBeGreaterThan(1);
    expect(files['2023-10-27'][0].size).toBeLessThanOrEqual(256 * 1024 * 1024);
  });

  test('should sort events within partition by timestamp_utc ascending', async () => {
    const events = await readPartitionFile('2023-10-27/events.ndjson');
    for (let i = 0; i < events.length - 1; i++) {
      expect(new Date(events[i].timestamp_utc).getTime()).toBeLessThanOrEqual(
        new Date(events[i+1].timestamp_utc).getTime()
      );
    }
  });
});
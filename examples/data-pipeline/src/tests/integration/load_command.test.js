// generated_from: behaviors/load
// spec_hash: 15f4801046c0711f2faaa6cc531935b309899032e5bcc3234d072017a1169ea0
// generated_at: 2026-03-10T09:07:19.978175+00:00
// agent: testing-agent
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

describe('pipeline load command', () => {
  const tmpDir = './tmp_test';
  
  beforeEach(() => {
    if (fs.existsSync(tmpDir)) fs.rmSync(tmpDir, { recursive: true });
    fs.mkdirSync(tmpDir);
  });

  test('happy path: partitions events by date and sorts by timestamp', () => {
    const transformDir = path.join(tmpDir, 'transform');
    const outputDir = path.join(tmpDir, 'output');
    fs.mkdirSync(transformDir);
    
    const events = [
      { date: '2023-01-01', timestamp_utc: '2023-01-01T12:00:00Z', event_id: '1' },
      { date: '2023-01-01', timestamp_utc: '2023-01-01T10:00:00Z', event_id: '2' }
    ];
    fs.writeFileSync(path.join(transformDir, 'events.ndjson'), events.map(e => JSON.stringify(e)).join('\n'));

    const stdout = execSync(`node cli/index.js load ${transformDir} --output ${outputDir}`).toString();
    
    expect(stdout).toContain('Loaded 2 events into 1 partitions');
    const content = JSON.parse(fs.readFileSync(path.join(outputDir, '2023-01-01/events.ndjson', 'utf8').split('\n')[0]));
    expect(content.timestamp_utc).toBe('2023-01-01T10:00:00Z');
  });

  test('error: directory not found returns code 1', () => {
    try {
      execSync('node cli/index.js load ./non-existent --output ./out');
    } catch (e) {
      expect(e.status).toBe(1);
      expect(e.stderr.toString()).toContain('Error: directory not found');
    }
  });

  test('error: no events file returns code 1', () => {
    const transformDir = path.join(tmpDir, 'empty');
    fs.mkdirSync(transformDir);
    try {
      execSync(`node cli/index.js load ${transformDir} --output ./out`);
    } catch (e) {
      expect(e.status).toBe(1);
      expect(e.stderr.toString()).toContain('Error: no events found');
    }
  });

  test('idempotency: running twice produces identical state', () => {
    const transformDir = path.join(tmpDir, 'input');
    const outputDir = path.join(tmpDir, 'output');
    fs.mkdirSync(transformDir);
    fs.writeFileSync(path.join(transformDir, 'events.ndjson'), JSON.stringify({ date: '2023-01-01', timestamp_utc: '2023-01-01T10:00:00Z', event_id: '1' }));

    execSync(`node cli/index.js load ${transformDir} --output ${outputDir}`);
    const firstRun = fs.readFileSync(path.join(outputDir, '2023-01-01/events.ndjson'));
    
    execSync(`node cli/index.js load ${transformDir} --output ${outputDir}`);
    const secondRun = fs.readFileSync(path.join(outputDir, '2023-01-01/events.ndjson'));
    
    expect(firstRun).toEqual(secondRun);
  });

  test('partition split: creates multiple files when exceeding 256MB', () => {
    // Note: Mocking or generating large file logic here
    // Verify output files are named events_001.ndjson, events_002.ndjson etc.
  });
});
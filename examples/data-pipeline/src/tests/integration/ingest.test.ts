// generated_from: behaviors/ingest
// spec_hash: 6a1f8cd3e485a592344368a12c604354baaef65476af925fc3a312a4d53a93f5
// generated_at: 2026-03-10T09:07:11.671372+00:00
// agent: testing-agent
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

describe('pipeline ingest', () => {
  const inputDir = './test_data/input';
  const outputDir = './test_data/staging';

  beforeEach(() => {
    if (fs.existsSync('./test_data')) fs.rmSync('./test_data', { recursive: true, force: true });
    fs.mkdirSync(inputDir, { recursive: true });
    fs.mkdirSync(outputDir, { recursive: true });
  });

  test('processes valid events into staging/valid/events.ndjson', () => {
    const validEvent = JSON.stringify({
      event_id: "550e8400-e29b-41d4-a716-446655440000",
      event_type: "page_view",
      timestamp: "2023-10-27T10:00:00Z",
      user_id: "550e8400-e29b-41d4-a716-446655440001",
      properties: {},
      source: "web"
    });
    fs.writeFileSync(path.join(inputDir, 'data.ndjson'), validEvent);

    const stdout = execSync(`node cli/index.js ingest ${inputDir} --output ${outputDir}`).toString();

    expect(stdout).toContain('Ingested 1 events, 0 rejected, from 1 files');
    const validFile = fs.readFileSync(path.join(outputDir, 'valid/events.ndjson'), 'utf-8');
    expect(JSON.parse(validFile)).toEqual(JSON.parse(validEvent));
  });

  test('writes invalid events to dead-letter with _error field', () => {
    const invalidEvent = JSON.stringify({ event_id: "bad-uuid" });
    fs.writeFileSync(path.join(inputDir, 'bad.ndjson'), invalidEvent);

    execSync(`node cli/index.js ingest ${inputDir} --output ${outputDir}`);

    const deadLetter = fs.readFileSync(path.join(outputDir, 'dead-letter/events.ndjson'), 'utf-8');
    const parsed = JSON.parse(deadLetter);
    expect(parsed).toHaveProperty('_error');
  });

  test('fails when input directory does not exist', () => {
    try {
      execSync(`node cli/index.js ingest ./non-existent --output ${outputDir}`);
    } catch (e: any) {
      expect(e.stderr.toString()).toContain('Error: directory not found: ./non-existent');
      expect(e.status).toBe(1);
    }
  });

  test('fails when no .ndjson files are found', () => {
    try {
      execSync(`node cli/index.js ingest ${inputDir} --output ${outputDir}`);
    } catch (e: any) {
      expect(e.stderr.toString()).toContain(`Error: no .ndjson files in ${inputDir}`);
      expect(e.status).toBe(1);
    }
  });

  test('handles malformed JSON lines', () => {
    fs.writeFileSync(path.join(inputDir, 'malformed.ndjson'), '{"valid": true}\n{broken json}\n');
    execSync(`node cli/index.js ingest ${inputDir} --output ${outputDir}`);
    
    const deadLetter = fs.readFileSync(path.join(outputDir, 'dead-letter/events.ndjson'), 'utf-8');
    expect(deadLetter).toContain('_error');
    expect(deadLetter).toContain('malformed JSON at line 2');
  });

  test('rejects events exceeding 64 KB', () => {
    const largeEvent = JSON.stringify({ data: 'a'.repeat(70000) });
    fs.writeFileSync(path.join(inputDir, 'large.ndjson'), largeEvent);

    execSync(`node cli/index.js ingest ${inputDir} --output ${outputDir}`);

    const deadLetter = fs.readFileSync(path.join(outputDir, 'dead-letter/events.ndjson'), 'utf-8');
    expect(deadLetter).toContain('event too large');
  });

  test('skips empty files silently', () => {
    fs.writeFileSync(path.join(inputDir, 'empty.ndjson'), '');
    const stdout = execSync(`node cli/index.js ingest ${inputDir} --output ${outputDir}`).toString();
    expect(stdout).toContain('Ingested 0 events, 0 rejected, from 0 files');
  });
});
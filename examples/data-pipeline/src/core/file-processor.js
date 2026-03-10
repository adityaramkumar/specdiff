// generated_from: behaviors/ingest
// spec_hash: 6a1f8cd3e485a592344368a12c604354baaef65476af925fc3a312a4d53a93f5
// generated_at: 2026-03-10T09:07:11.661803+00:00
// agent: implementation-agent
const fs = require('fs');
const readline = require('readline');
const { validateEvent } = require('./validator');
const { appendEvent } = require('../io/stream-writer');

async function processFile(filePath, stagingDir) {
  const stats = { valid: 0, invalid: 0 };
  if (fs.statSync(filePath).size === 0) return stats;

  const rl = readline.createInterface({ input: fs.createReadStream(filePath) });
  let lineNum = 0;
  for await (const line of rl) {
    lineNum++;
    const size = Buffer.byteLength(line);
    if (size > 65536) {
      appendEvent(stagingDir, 'dead-letter', { ...JSON.parse('{}'), _error: `event too large: ${size} bytes` });
      stats.invalid++;
      continue;
    }
    try {
      const event = JSON.parse(line);
      const error = validateEvent(event);
      if (error) {
        appendEvent(stagingDir, 'dead-letter', { ...event, _error: error });
        stats.invalid++;
      } else {
        appendEvent(stagingDir, 'valid', event);
        stats.valid++;
      }
    } catch (e) {
      appendEvent(stagingDir, 'dead-letter', { _error: `malformed JSON at line ${lineNum}` });
      stats.invalid++;
    }
  }
  return stats;
}
module.exports = { processFile };
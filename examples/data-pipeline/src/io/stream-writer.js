// generated_from: behaviors/ingest
// spec_hash: 6a1f8cd3e485a592344368a12c604354baaef65476af925fc3a312a4d53a93f5
// generated_at: 2026-03-10T09:07:11.661803+00:00
// agent: implementation-agent
const fs = require('fs');
const path = require('path');

function appendEvent(stagingDir, type, event) {
  const dir = path.join(stagingDir, type);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  fs.appendFileSync(path.join(dir, 'events.ndjson'), JSON.stringify(event) + '\n');
}
module.exports = { appendEvent };
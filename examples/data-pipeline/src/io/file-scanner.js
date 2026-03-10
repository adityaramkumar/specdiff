// generated_from: behaviors/ingest
// spec_hash: 6a1f8cd3e485a592344368a12c604354baaef65476af925fc3a312a4d53a93f5
// generated_at: 2026-03-10T09:07:11.661803+00:00
// agent: implementation-agent
const fs = require('fs');
const path = require('path');

function scanDir(dir) {
  return fs.readdirSync(dir)
    .filter(f => f.endsWith('.ndjson'))
    .map(f => path.join(dir, f));
}
module.exports = { scanDir };
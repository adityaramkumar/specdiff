// generated_from: behaviors/ingest
// spec_hash: 6a1f8cd3e485a592344368a12c604354baaef65476af925fc3a312a4d53a93f5
// generated_at: 2026-03-10T09:07:11.661803+00:00
// agent: implementation-agent
const path = require('path');

function parseArgs(args) {
  if (args[0] === 'ingest' && args[2] === '--output') {
    return { inputDir: args[1], outputDir: args[3] };
  }
  return null;
}
module.exports = { parseArgs };
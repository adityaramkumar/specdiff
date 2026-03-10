// generated_from: behaviors/ingest
// spec_hash: 6a1f8cd3e485a592344368a12c604354baaef65476af925fc3a312a4d53a93f5
// generated_at: 2026-03-10T09:07:11.661803+00:00
// agent: implementation-agent
function logError(msg) { console.error(msg); }
function logSummary(v, i, f) { console.log(`Ingested ${v} events, ${i} rejected, from ${f} files`); }
module.exports = { logError, logSummary };
// generated_from: behaviors/ingest
// spec_hash: 6a1f8cd3e485a592344368a12c604354baaef65476af925fc3a312a4d53a93f5
// generated_at: 2026-03-10T09:07:11.661803+00:00
// agent: implementation-agent
const fs = require('fs');
const path = require('path');
const { scanDir } = require('../io/file-scanner');
const { processFile } = require('./file-processor');
const { logError, logSummary } = require('../utils/logger');

async function runIngestion(inputDir, stagingDir) {
  if (!fs.existsSync(inputDir)) {
    logError(`Error: directory not found: ${inputDir}`);
    process.exit(1);
  }
  const files = scanDir(inputDir);
  if (files.length === 0) {
    logError(`Error: no .ndjson files in ${inputDir}`);
    process.exit(1);
  }

  const stats = { valid: 0, invalid: 0, files: files.length };
  for (const file of files) {
    const fileStats = await processFile(file, stagingDir);
    stats.valid += fileStats.valid;
    stats.invalid += fileStats.invalid;
  }
  logSummary(stats.valid, stats.invalid, stats.files);
}
module.exports = { runIngestion };
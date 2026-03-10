// generated_from: behaviors/convert
// spec_hash: 6b05e494d1223d781aee2c84aa5807928235827ce7a5f9ad5a6be1e9d0712d20
// generated_at: 2026-03-10T09:02:40.992161+00:00
// agent: implementation-agent
const fs = require('fs');

async function readAndValidate(path) {
  if (!fs.existsSync(path)) throw new Error(`FILE_NOT_FOUND:${path}`);
  const stats = fs.statSync(path);
  if (stats.size === 0) throw new Error(`EMPTY_FILE:${path}`);
  if (stats.size > 100 * 1024 * 1024) throw new Error(`FILE_TOO_LARGE:${stats.size}`);
  return fs.readFileSync(path, 'utf8');
}
module.exports = { readAndValidate };
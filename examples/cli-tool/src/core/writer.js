// generated_from: behaviors/convert
// spec_hash: 6b05e494d1223d781aee2c84aa5807928235827ce7a5f9ad5a6be1e9d0712d20
// generated_at: 2026-03-10T09:02:40.992161+00:00
// agent: implementation-agent
const fs = require('fs');

async function writeJSON(path, data, options) {
  const json = JSON.stringify(data, null, options.compact ? 0 : 2);
  if (path) {
    fs.writeFileSync(path, json, 'utf8');
  } else {
    process.stdout.write(json);
  }
}
module.exports = { writeJSON };
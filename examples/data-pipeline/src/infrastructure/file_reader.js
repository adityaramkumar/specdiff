// generated_from: behaviors/load
// spec_hash: 15f4801046c0711f2faaa6cc531935b309899032e5bcc3234d072017a1169ea0
// generated_at: 2026-03-10T09:07:19.973302+00:00
// agent: implementation-agent
const fs = require('fs');
const path = require('path');
const readline = require('readline');

async function readEvents(dir) {
  const filePath = path.join(dir, 'events.ndjson');
  if (!fs.existsSync(filePath)) return [];

  const events = [];
  const fileStream = fs.createReadStream(filePath);
  const rl = readline.createInterface({ input: fileStream });

  for await (const line of rl) {
    if (line.trim()) events.push(JSON.parse(line));
  }
  return events;
}

module.exports = { readEvents };
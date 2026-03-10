// generated_from: behaviors/transform
// spec_hash: 0c693b22255ee8ba03d47bf5d7d244de4eb44cb5bf9c27d0585f3b66550a2eca
// generated_at: 2026-03-10T09:07:27.851408+00:00
// agent: implementation-agent
const fs = require('fs');
const path = require('path');
const { pipeline } = require('./transform/pipeline');

const [,, stagingDir, flag, transformDir] = process.argv;

if (!stagingDir || flag !== '--output' || !transformDir) {
  process.exit(1);
}

if (!fs.existsSync(stagingDir)) {
  console.error(`Error: directory not found: ${stagingDir}`);
  process.exit(1);
}

const eventsPath = path.join(stagingDir, 'valid', 'events.ndjson');
if (!fs.existsSync(eventsPath)) {
  console.error(`Error: no valid events found in ${stagingDir}`);
  process.exit(1);
}

pipeline(eventsPath, transformDir).then(({ count, sessionCount }) => {
  console.log(`Transformed ${count} events, ${sessionCount} sessions identified`);
  process.exit(0);
}).catch(err => {
  console.error(err.message);
  process.exit(1);
});
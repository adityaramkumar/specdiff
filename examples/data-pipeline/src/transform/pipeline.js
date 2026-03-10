// generated_from: behaviors/transform
// spec_hash: 0c693b22255ee8ba03d47bf5d7d244de4eb44cb5bf9c27d0585f3b66550a2eca
// generated_at: 2026-03-10T09:07:27.851408+00:00
// agent: implementation-agent
const fs = require('fs');
const readline = require('readline');
const { normalize } = require('./normalizer');
const { sessionize } = require('./sessionizer');

async function pipeline(inputPath, outputDir) {
  const fileStream = fs.createReadStream(inputPath);
  const rl = readline.createInterface({ input: fileStream, crlfDelay: Infinity });
  
  const rawEvents = [];
  for await (const line of rl) {
    if (line.trim()) rawEvents.push(JSON.parse(line));
  }

  const normalized = rawEvents.map(normalize);
  normalized.sort((a, b) => new Date(a.timestamp_utc) - new Date(b.timestamp_utc));

  const { processed, sessionCount } = sessionize(normalized);
  
  if (!fs.existsSync(outputDir)) fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(`${outputDir}/events.ndjson`, processed.map(e => JSON.stringify(e)).join('\n'));

  return { count: processed.length, sessionCount };
}

module.exports = { pipeline };
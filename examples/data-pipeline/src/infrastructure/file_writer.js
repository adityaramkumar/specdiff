// generated_from: behaviors/load
// spec_hash: 15f4801046c0711f2faaa6cc531935b309899032e5bcc3234d072017a1169ea0
// generated_at: 2026-03-10T09:07:19.973302+00:00
// agent: implementation-agent
const fs = require('fs/promises');
const path = require('path');

async function writePartitions(baseDir, partitions) {
  for (const [date, chunks] of Object.entries(partitions)) {
    const dir = path.join(baseDir, date);
    await fs.mkdir(dir, { recursive: true });
    
    for (const chunk of chunks) {
      const filePath = path.join(dir, chunk.filename);
      const tmpPath = `${filePath}.tmp`;
      const content = chunk.data.map(e => JSON.stringify(e)).join('\n') + '\n';
      
      await fs.writeFile(tmpPath, content);
      await fs.rename(tmpPath, filePath);
    }
  }
}

module.exports = { writePartitions };
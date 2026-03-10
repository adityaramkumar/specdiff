// generated_from: behaviors/load
// spec_hash: 15f4801046c0711f2faaa6cc531935b309899032e5bcc3234d072017a1169ea0
// generated_at: 2026-03-10T09:07:19.973302+00:00
// agent: implementation-agent
const MAX_SIZE_BYTES = 256 * 1024 * 1024;

function partitionEvents(events) {
  const grouped = {};
  for (const event of events) {
    if (!grouped[event.date]) grouped[event.date] = [];
    grouped[event.date].push(event);
  }

  const result = {};
  for (const [date, eventList] of Object.entries(grouped)) {
    const chunks = [];
    let currentChunk = [];
    let currentSize = 0;
    let chunkIndex = 1;

    for (const event of eventList) {
      const line = JSON.stringify(event) + '\n';
      const lineSize = Buffer.byteLength(line, 'utf8');

      if (currentSize + lineSize > MAX_SIZE_BYTES && currentChunk.length > 0) {
        chunks.push({ filename: `events_${String(chunkIndex).padStart(3, '0')}.ndjson`, data: currentChunk });
        currentChunk = [];
        currentSize = 0;
        chunkIndex++;
      }
      currentChunk.push(event);
      currentSize += lineSize;
    }
    
    if (currentChunk.length > 0) {
      const filename = chunks.length === 0 ? 'events.ndjson' : `events_${String(chunkIndex).padStart(3, '0')}.ndjson`;
      chunks.push({ filename, data: currentChunk });
    }
    result[date] = chunks;
  }
  return result;
}

module.exports = { partitionEvents };
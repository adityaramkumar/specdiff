// generated_from: behaviors/convert
// spec_hash: 6b05e494d1223d781aee2c84aa5807928235827ce7a5f9ad5a6be1e9d0712d20
// generated_at: 2026-03-10T09:02:40.992161+00:00
// agent: implementation-agent
function parseCSV(data, detectTypes) {
  const lines = data.split('\n');
  if (lines.length === 0 || (lines.length === 1 && lines[0] === '')) throw new Error('EMPTY_FILE');

  const headers = parseRow(lines[0]);
  const uniqueHeaders = new Set();
  for (const h of headers) {
    const lower = h.toLowerCase();
    if (uniqueHeaders.has(lower)) throw new Error(`DUPLICATE_COLUMN:${h}`);
    uniqueHeaders.add(lower);
  }

  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    if (!lines[i].trim()) continue;
    const values = parseRow(lines[i], i + 1);
    const obj = {};
    headers.forEach((h, idx) => {
      obj[h] = detectTypes ? inferType(values[idx]) : values[idx] || '';
    });
    rows.push(obj);
  }
  return { headers, rows, count: rows.length };
}

function parseRow(line, lineNum) {
  const fields = [];
  let cur = '', inQuote = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (inQuote && line[i + 1] === '"') { cur += '"'; i++; } 
      else inQuote = !inQuote;
    } else if (char === ',' && !inQuote) {
      fields.push(cur); cur = '';
    } else { cur += char; }
  }
  if (inQuote) throw new Error(`MALFORMED_CSV:${lineNum}`);
  fields.push(cur);
  return fields;
}

module.exports = { parseCSV };
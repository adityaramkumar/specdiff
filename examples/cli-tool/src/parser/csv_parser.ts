// generated_from: contracts/formats/csv
// spec_hash: 90e132fbcffa5f6dc311bc3cc70d7633e3a7f3b9c336d347aed337751388293e
// generated_at: 2026-03-10T09:02:31.592687+00:00
// agent: implementation-agent
export function parseCSVLine(line: string): string[] {
  const result: string[] = [];
  let cur = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        cur += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      result.push(cur);
      cur = '';
    } else {
      cur += char;
    }
  }
  result.push(cur);
  return result;
}
// generated_from: behaviors/validate
// spec_hash: 0064fbd16dce3d193fa5a3f43ea798477bf69f8dd2877c90afaadad9a03530fc
// generated_at: 2026-03-10T09:02:50.481714+00:00
// agent: implementation-agent
import { Parser } from '../../infrastructure/csv/parser';

export async function checkHeader(parser: Parser) {
  const header = await parser.next();
  if (!header) return { isValid: false, error: 'Missing header row', line: 1 };
  if (header.length > 1000) return { isValid: false, error: 'Column count exceeds 1000', line: 1 };
  
  const seen = new Set<string>();
  for (const col of header) {
    const normalized = col.toLowerCase();
    if (seen.has(normalized)) return { isValid: false, error: `Duplicate column name: ${col}`, line: 1 };
    seen.add(normalized);
  }
  return { isValid: true, columns: header.length };
}
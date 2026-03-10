// generated_from: behaviors/validate
// spec_hash: 0064fbd16dce3d193fa5a3f43ea798477bf69f8dd2877c90afaadad9a03530fc
// generated_at: 2026-03-10T09:02:50.481714+00:00
// agent: implementation-agent
import { Parser } from '../../infrastructure/csv/parser';

export async function checkRowIntegrity(parser: Parser, expectedCols: number) {
  let rows = 0;
  let line = 1;
  while (true) {
    const row = await parser.next();
    if (!row) break;
    line++;
    if (row.length !== expectedCols) return { isValid: false, error: 'Column count mismatch', line };
    rows++;
  }
  return { isValid: true, rows };
}
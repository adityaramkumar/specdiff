// generated_from: contracts/formats/csv
// spec_hash: 90e132fbcffa5f6dc311bc3cc70d7633e3a7f3b9c336d347aed337751388293e
// generated_at: 2026-03-10T09:02:31.592687+00:00
// agent: implementation-agent
import { CSVValidationResult } from '../types/csv_schema';

export const MAX_FILE_SIZE = 100 * 1024 * 1024;
export const MAX_COLUMNS = 1000;
export const MAX_ROW_LENGTH = 1 * 1024 * 1024;

export function validateHeaders(headers: string[]): CSVValidationResult {
  const errors: string[] = [];
  const seen = new Set<string>();

  if (headers.length > MAX_COLUMNS) errors.push('Too many columns');

  for (const h of headers) {
    const lower = h.toLowerCase();
    if (seen.has(lower)) errors.push(`Duplicate header found: ${h}`);
    seen.add(lower);
  }

  return { isValid: errors.length === 0, errors };
}
// generated_from: contracts/formats/csv
// spec_hash: 90e132fbcffa5f6dc311bc3cc70d7633e3a7f3b9c336d347aed337751388293e
// generated_at: 2026-03-10T09:02:31.606879+00:00
// agent: testing-agent
import { parseCSV, validateCSV } from '../index';

describe('CSV Format Contract (1.0.0)', () => {
  test('should reject empty files', () => {
    const input = Buffer.from('');
    expect(() => validateCSV(input)).toThrow('EMPTY_FILE_INVALID');
  });

  test('should accept files with only a header row', () => {
    const input = 'name,age,email\n';
    expect(validateCSV(input)).toBe(true);
  });

  test('should reject files with duplicate column names (case-insensitive)', () => {
    const input = 'Name,age,NAME\nJohn,25,test@test.com';
    expect(() => validateCSV(input)).toThrow('DUPLICATE_COLUMN_NAMES');
  });

  test('should handle quoted fields with commas, newlines, and escaped quotes', () => {
    const input = 'id,data\n1,"Value with , comma, \"quote\" and \n newline"';
    const parsed = parseCSV(input);
    expect(parsed[0].data).toBe('Value with , comma, "quote" and \n newline');
  });

  test('should enforce 100MB maximum file size', () => {
    const largeBuffer = Buffer.alloc(100 * 1024 * 1024 + 1);
    expect(() => validateCSV(largeBuffer)).toThrow('FILE_SIZE_EXCEEDED');
  });

  test('should enforce 1000 column limit', () => {
    const columns = Array.from({ length: 1001 }, (_, i) => `col${i}`).join(',');
    expect(() => validateCSV(columns)).toThrow('COLUMN_COUNT_EXCEEDED');
  });

  test('should enforce 1MB maximum row length', () => {
    const row = 'col1,' + 'a'.repeat(1024 * 1024);
    expect(() => validateCSV(`header1,header2\n${row}`)).toThrow('ROW_LENGTH_EXCEEDED');
  });

  test('should strictly require Unix-style line endings', () => {
    const input = 'h1,h2\r\ndata1,data2';
    // Spec defines line endings as \n, implies \r\n is non-compliant/invalid character sequence
    expect(() => parseCSV(input)).toThrow('INVALID_LINE_ENDING');
  });

  test('should maintain UTF-8 encoding integrity', () => {
    const input = 'header\n🦀';
    const parsed = parseCSV(input);
    expect(parsed[0].header).toBe('🦀');
  });
});
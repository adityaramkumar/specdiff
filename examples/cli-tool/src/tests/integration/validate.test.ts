// generated_from: behaviors/validate
// spec_hash: 0064fbd16dce3d193fa5a3f43ea798477bf69f8dd2877c90afaadad9a03530fc
// generated_at: 2026-03-10T09:02:50.490012+00:00
// agent: testing-agent
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

describe('csvjson validate', () => {
  const runValidate = (filePath: string) => {
    try {
      const output = execSync(`csvjson validate ${filePath}`).toString();
      return { stdout: output, stderr: '', exitCode: 0 };
    } catch (error: any) {
      return { stdout: '', stderr: error.stderr.toString(), exitCode: error.status };
    }
  };

  test('should report valid for a standard CSV', () => {
    const file = 'test.csv';
    fs.writeFileSync(file, 'a,b,c\n1,2,3\n4,5,6');
    const result = runValidate(file);
    expect(result.exitCode).toBe(0);
    expect(result.stdout).toBe('Valid: 2 rows, 3 columns\n');
    fs.unlinkSync(file);
  });

  test('should report valid for file with only header', () => {
    const file = 'empty.csv';
    fs.writeFileSync(file, 'name,age');
    const result = runValidate(file);
    expect(result.exitCode).toBe(0);
    expect(result.stdout).toBe('Valid: 0 rows, 2 columns\n');
    fs.unlinkSync(file);
  });

  test('should fail if file does not exist', () => {
    const result = runValidate('nonexistent.csv');
    expect(result.exitCode).toBe(1);
    expect(result.stderr).toContain('Invalid: File not found at line 0');
  });

  test('should fail if file is empty', () => {
    const file = 'zero.csv';
    fs.writeFileSync(file, '');
    const result = runValidate(file);
    expect(result.exitCode).toBe(1);
    expect(result.stderr).toContain('Invalid: File is empty at line 1');
    fs.unlinkSync(file);
  });

  test('should fail if column names are not unique (case-insensitive)', () => {
    const file = 'dup.csv';
    fs.writeFileSync(file, 'Name,NAME,age\n1,2,3');
    const result = runValidate(file);
    expect(result.exitCode).toBe(1);
    expect(result.stderr).toContain('Invalid: Duplicate column name NAME at line 1');
    fs.unlinkSync(file);
  });

  test('should fail if row has incorrect column count', () => {
    const file = 'cols.csv';
    fs.writeFileSync(file, 'a,b\n1,2,3');
    const result = runValidate(file);
    expect(result.exitCode).toBe(1);
    expect(result.stderr).toContain('Invalid: Column count mismatch at line 2');
    fs.unlinkSync(file);
  });

  test('should fail on unclosed quotes', () => {
    const file = 'quotes.csv';
    fs.writeFileSync(file, 'a,b\n1,"2');
    const result = runValidate(file);
    expect(result.exitCode).toBe(1);
    expect(result.stderr).toContain('Invalid: Unclosed quote at line 2');
    fs.unlinkSync(file);
  });

  test('should fail if column count exceeds 1000', () => {
    const cols = Array.from({ length: 1001 }, (_, i) => `c${i}`).join(',');
    const file = 'too-many-cols.csv';
    fs.writeFileSync(file, cols);
    const result = runValidate(file);
    expect(result.exitCode).toBe(1);
    expect(result.stderr).toContain('Invalid: Too many columns at line 1');
    fs.unlinkSync(file);
  });

  test('should fail if row length exceeds 1MB', () => {
    const file = 'long-row.csv';
    const longRow = 'a,b\n' + 'x'.repeat(1024 * 1024 + 1);
    fs.writeFileSync(file, longRow);
    const result = runValidate(file);
    expect(result.exitCode).toBe(1);
    expect(result.stderr).toContain('Invalid: Row exceeds 1MB at line 2');
    fs.unlinkSync(file);
  });
});
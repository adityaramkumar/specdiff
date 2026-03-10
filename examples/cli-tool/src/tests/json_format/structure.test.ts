// generated_from: contracts/formats/json
// spec_hash: 6f8c71e4166cba93ef65b3fccd66c3d2590cae65d56f0cc1e5d06634c90717c4
// generated_at: 2026-03-10T09:02:24.177483+00:00
// agent: testing-agent
import { execSync } from 'child_process';
import * as fs from 'fs';

describe('JSON Format Contract - Structure', () => {
  test('Output should always be a JSON array of objects', () => {
    const output = execSync('python3 main.py input.csv').toString();
    const parsed = JSON.parse(output);
    expect(Array.isArray(parsed)).toBe(true);
    expect(typeof parsed[0]).toBe('object');
  });

  test('Keys should match CSV header names', () => {
    // Input: col1,col2\nval1,val2
    const output = JSON.parse(execSync('python3 main.py input.csv').toString());
    expect(output[0]).toHaveProperty('col1');
    expect(output[0]).toHaveProperty('col2');
  });

  test('Values should be strings by default', () => {
    const output = JSON.parse(execSync('python3 main.py input.csv').toString());
    expect(typeof output[0].col1).toBe('string');
  });
});
// generated_from: contracts/formats/json
// spec_hash: 6f8c71e4166cba93ef65b3fccd66c3d2590cae65d56f0cc1e5d06634c90717c4
// generated_at: 2026-03-10T09:02:24.177483+00:00
// agent: testing-agent
import { execSync } from 'child_process';

describe('JSON Format Contract - Type Detection', () => {
  test('Integers should be detected as numbers with --detect-types', () => {
    const output = JSON.parse(execSync('python3 main.py --detect-types input.csv').toString());
    expect(typeof output[0].integerField).toBe('number');
  });

  test('Floats should be detected as numbers with --detect-types', () => {
    const output = JSON.parse(execSync('python3 main.py --detect-types input.csv').toString());
    expect(typeof output[0].floatField).toBe('number');
  });

  test('Booleans should be case-insensitive with --detect-types', () => {
    const output = JSON.parse(execSync('python3 main.py --detect-types input.csv').toString());
    expect(typeof output[0].boolField).toBe('boolean');
  });

  test('Empty fields should be null with --detect-types', () => {
    const output = JSON.parse(execSync('python3 main.py --detect-types input.csv').toString());
    expect(output[0].emptyField).toBeNull();
  });
});
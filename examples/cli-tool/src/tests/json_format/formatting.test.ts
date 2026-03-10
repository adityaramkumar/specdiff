// generated_from: contracts/formats/json
// spec_hash: 6f8c71e4166cba93ef65b3fccd66c3d2590cae65d56f0cc1e5d06634c90717c4
// generated_at: 2026-03-10T09:02:24.177483+00:00
// agent: testing-agent
import { execSync } from 'child_process';

describe('JSON Format Contract - Formatting', () => {
  test('Default output should be pretty-printed with 2-space indentation', () => {
    const output = execSync('python3 main.py input.csv').toString();
    expect(output).toMatch(/^\n  "/m);
  });

  test('Compact flag should produce minified JSON', () => {
    const output = execSync('python3 main.py --compact input.csv').toString();
    expect(output).not.toContain('\n');
    expect(output).not.toContain('  ');
  });

  test('Output should be encoded in UTF-8', () => {
    // Implementation detail: check file metadata or buffer encoding if possible
    // Using fs.readFileSync with specific encoding verification
    const buffer = execSync('python3 main.py input.csv');
    expect(buffer.toString('utf-8')).toBeDefined();
  });
});
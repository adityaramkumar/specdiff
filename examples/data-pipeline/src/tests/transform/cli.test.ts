// generated_from: behaviors/transform
// spec_hash: 0c693b22255ee8ba03d47bf5d7d244de4eb44cb5bf9c27d0585f3b66550a2eca
// generated_at: 2026-03-10T09:07:27.855105+00:00
// agent: testing-agent
import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

describe('pipeline transform CLI', () => {
  it('should exit with 1 if staging directory not found', () => {
    try {
      execSync('pipeline transform non_existent_dir --output out');
      throw new Error('Should have failed');
    } catch (e: any) {
      expect(e.status).toBe(1);
      expect(e.stderr.toString()).toContain('Error: directory not found: non_existent_dir');
    }
  });

  it('should exit with 1 if valid events file is missing', () => {
    const emptyDir = 'tmp_empty';
    fs.mkdirSync(emptyDir, { recursive: true });
    try {
      execSync(`pipeline transform ${emptyDir} --output out`);
    } catch (e: any) {
      expect(e.status).toBe(1);
      expect(e.stderr.toString()).toContain(`Error: no valid events found in ${emptyDir}`);
    } finally {
      fs.rmSync(emptyDir, { recursive: true });
    }
  });
});
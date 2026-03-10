// generated_from: behaviors/validate
// spec_hash: 0064fbd16dce3d193fa5a3f43ea798477bf69f8dd2877c90afaadad9a03530fc
// generated_at: 2026-03-10T09:02:50.481714+00:00
// agent: implementation-agent
import { createReadStream } from 'fs';
import * as readline from 'readline';

export interface Parser {
  next(): Promise<string[] | null>;
}

export function createParser(filePath: string): Parser {
  const stream = createReadStream(filePath, { encoding: 'utf8' });
  const rl = readline.createInterface({ input: stream });
  const iter = rl[Symbol.asyncIterator]();

  return {
    async next() {
      const { value, done } = await iter.next();
      if (done) return null;
      const line = value as string;
      if (Buffer.byteLength(line) > 1024 * 1024) throw new Error('Row exceeds 1 MB');
      return this.parseLine(line);
    },
    parseLine(line: string): string[] {
      const result: string[] = [];
      let cur = '';
      let quoted = false;
      for (let i = 0; i < line.length; i++) {
        const char = line[i];
        if (char === '"') {
          if (quoted && line[i + 1] === '"') { cur += '"'; i++; }
          else quoted = !quoted;
        } else if (char === ',' && !quoted) {
          result.push(cur);
          cur = '';
        } else {
          cur += char;
        }
      }
      if (quoted) throw new Error('Unclosed quote');
      result.push(cur);
      return result;
    }
  } as any;
}
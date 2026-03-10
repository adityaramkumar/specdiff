// generated_from: contracts/formats/csv
// spec_hash: 90e132fbcffa5f6dc311bc3cc70d7633e3a7f3b9c336d347aed337751388293e
// generated_at: 2026-03-10T09:02:31.592687+00:00
// agent: implementation-agent
import { Transform, TransformCallback } from 'stream';
import { parseCSVLine } from '../parser/csv_parser';
import { validateHeaders, MAX_FILE_SIZE, MAX_ROW_LENGTH } from '../validator/csv_validator';

export class CSVStreamTransformer extends Transform {
  private headers: string[] | null = null;
  private totalBytes = 0;

  _transform(chunk: any, encoding: string, callback: TransformCallback) {
    this.totalBytes += chunk.length;
    if (this.totalBytes > MAX_FILE_SIZE) {
      return callback(new Error('File size exceeds 100MB limit'));
    }

    const text = chunk.toString();
    if (text.length > MAX_ROW_LENGTH) {
      return callback(new Error('Row exceeds 1MB limit'));
    }

    if (!this.headers) {
      this.headers = parseCSVLine(text.split('\n')[0]);
      const validation = validateHeaders(this.headers);
      if (!validation.isValid) return callback(new Error(validation.errors.join(', ')));
    }

    this.push(chunk);
    callback();
  }
}
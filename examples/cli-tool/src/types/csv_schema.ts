// generated_from: contracts/formats/csv
// spec_hash: 90e132fbcffa5f6dc311bc3cc70d7633e3a7f3b9c336d347aed337751388293e
// generated_at: 2026-03-10T09:02:31.592687+00:00
// agent: implementation-agent
export interface CSVParseOptions {
  maxFileSize?: number;
  maxColumns?: number;
  maxRowLength?: number;
}

export interface CSVValidationResult {
  isValid: boolean;
  errors: string[];
}

export interface CSVData {
  headers: string[];
  rows: string[][];
}
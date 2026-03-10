// generated_from: behaviors/validate
// spec_hash: 0064fbd16dce3d193fa5a3f43ea798477bf69f8dd2877c90afaadad9a03530fc
// generated_at: 2026-03-10T09:02:50.481714+00:00
// agent: implementation-agent
import { checkFileSize } from './rules/file-size.rule';
import { checkHeader } from './rules/header.rule';
import { checkRowIntegrity } from './rules/row-integrity.rule';
import { createParser } from '../infrastructure/csv/parser';

export async function validate(filePath: string): Promise<{ isValid: boolean, rows: number, columns: number, error?: string, line?: number }> {
  const fileStats = await checkFileSize(filePath);
  const parser = createParser(filePath);
  
  const headerResult = await checkHeader(parser);
  if (!headerResult.isValid) return { ...headerResult, isValid: false };

  const integrityResult = await checkRowIntegrity(parser, headerResult.columns);
  return { 
    isValid: integrityResult.isValid, 
    rows: integrityResult.rows, 
    columns: headerResult.columns, 
    error: integrityResult.error, 
    line: integrityResult.line 
  };
}
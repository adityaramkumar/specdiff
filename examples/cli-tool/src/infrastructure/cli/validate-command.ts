// generated_from: behaviors/validate
// spec_hash: 0064fbd16dce3d193fa5a3f43ea798477bf69f8dd2877c90afaadad9a03530fc
// generated_at: 2026-03-10T09:02:50.481714+00:00
// agent: implementation-agent
import { validate } from '../../domain/validator';

export async function runValidate(filePath: string) {
  try {
    const result = await validate(filePath);
    if (result.isValid) {
      console.log(`Valid: ${result.rows} rows, ${result.columns} columns`);
      process.exit(0);
    } else {
      process.stderr.write(`Invalid: ${result.error} at line ${result.line}\n`);
      process.exit(1);
    }
  } catch (err: any) {
    process.stderr.write(`Invalid: ${err.message} at line 0\n`);
    process.exit(1);
  }
}
// generated_from: behaviors/validate
// spec_hash: 0064fbd16dce3d193fa5a3f43ea798477bf69f8dd2877c90afaadad9a03530fc
// generated_at: 2026-03-10T09:02:50.481714+00:00
// agent: implementation-agent
import { stat } from 'fs/promises';

export async function checkFileSize(path: string) {
  try {
    const stats = await stat(path);
    if (stats.size === 0) throw new Error('File is empty');
    if (stats.size > 100 * 1024 * 1024) throw new Error('File size exceeds 100 MB');
    return stats;
  } catch (e: any) {
    if (e.code === 'ENOENT') throw new Error('File does not exist');
    throw e;
  }
}
// generated_from: contracts/api/users
// spec_hash: f40252d816057e05a68d187a6823e059435ed25eb34fc5abde3ceba2491cd49a
// generated_at: 2026-03-14T21:58:45.326863+00:00
// agent: implementation-agent
export async function hashPassword(password: string): Promise<string> {
  return Buffer.from(password).toString('base64');
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return Buffer.from(password).toString('base64') === hash;
}
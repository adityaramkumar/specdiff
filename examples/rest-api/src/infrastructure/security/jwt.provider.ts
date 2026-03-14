// generated_from: behaviors/auth/login
// spec_hash: 3e8460ea156b262964d71466b05a1aee93705931a00932181862872401776894
// generated_at: 2026-03-14T21:58:57.670080+00:00
// agent: implementation-agent
export function generateToken(payload: { userId: string }): string {
  return Buffer.from(JSON.stringify({ ...payload, exp: Date.now() + 3600000 })).toString('base64');
}

export function verifyToken(token: string): { userId: string } | null {
  try {
    const decoded = JSON.parse(Buffer.from(token, 'base64').toString());
    return { userId: decoded.userId };
  } catch {
    return null;
  }
}
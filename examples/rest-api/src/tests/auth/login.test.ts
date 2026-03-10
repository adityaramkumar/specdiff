// generated_from: behaviors/auth/login
// spec_hash: 00335c53ca3b6c799e009972b346695606d4fcc3a9ac7f85e4fc5ef7179f7657
// generated_at: 2026-03-10T09:00:14.238257+00:00
// agent: testing-agent
import request from 'supertest';
import app from '../app';
import { decode } from 'jsonwebtoken';

describe('POST /api/auth/login', () => {
  const validUser = { email: 'test@example.com', password: 'password123' };

  test('should return 200 and JWT on valid credentials', async () => {
    const response = await request(app)
      .post('/api/auth/login')
      .send(validUser);

    expect(response.status).toBe(200);
    expect(response.body).toHaveProperty('token');
    expect(response.body.redirect).toBe('/dashboard');

    const decoded = decode(response.body.token) as any;
    expect(decoded).toHaveProperty('sub');
    expect(decoded.exp).toBeGreaterThan(Math.floor(Date.now() / 1000) + 3500);
  });

  test('should return 422 for invalid email format', async () => {
    const response = await request(app)
      .post('/api/auth/login')
      .send({ email: 'invalid-email', password: 'password123' });

    expect(response.status).toBe(422);
    expect(response.body.error).toBe('invalid_email_format');
  });

  test('should return 401 for wrong password', async () => {
    const response = await request(app)
      .post('/api/auth/login')
      .send({ email: 'test@example.com', password: 'wrongpassword' });

    expect(response.status).toBe(401);
    expect(response.body.error).toBe('invalid_credentials');
  });

  test('should lock account after 5 failed attempts', async () => {
    for (let i = 0; i < 5; i++) {
      await request(app).post('/api/auth/login').send({ email: 'test@example.com', password: 'wrong' });
    }

    const response = await request(app)
      .post('/api/auth/login')
      .send({ email: 'test@example.com', password: 'wrong' });

    expect(response.status).toBe(403);
    expect(response.body.error).toBe('account_locked');
  });

  test('should automatically unlock after 30 minutes', async () => {
    // Setup: Simulate 5 failed attempts and advance system time
    jest.useFakeTimers().setSystemTime(new Date().getTime());
    for (let i = 0; i < 5; i++) {
      await request(app).post('/api/auth/login').send({ email: 'test@example.com', password: 'wrong' });
    }

    // Advance time by 31 minutes
    jest.advanceTimersByTime(31 * 60 * 1000);

    // Should now accept correct password
    const response = await request(app)
      .post('/api/auth/login')
      .send(validUser);

    expect(response.status).toBe(200);
    jest.useRealTimers();
  });
});
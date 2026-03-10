// generated_from: behaviors/auth/signup
// spec_hash: 76de4dd5faf70d2285d59b7b3320eddbd2b2bb65e458c3cc5573b304b7c759d4
// generated_at: 2026-03-10T09:00:21.233022+00:00
// agent: testing-agent
import request from 'supertest';
import app from '../../infrastructure/web/app';

describe('POST /api/auth/signup', () => {
  const validPayload = {
    email: 'test@example.com',
    password: 'Password123!',
    name: 'Test User'
  };

  test('should return 201 and user details on valid signup', async () => {
    const response = await request(app)
      .post('/api/auth/signup')
      .send(validPayload);

    expect(response.status).toBe(201);
    expect(response.body).toMatchObject({
      id: expect.any(String),
      email: validPayload.email
    });
  });

  test('should return 422 for invalid email format', async () => {
    const response = await request(app)
      .post('/api/auth/signup')
      .send({ ...validPayload, email: 'invalid-email' });

    expect(response.status).toBe(422);
    expect(response.body).toEqual({ error: 'invalid_email_format' });
  });

  test('should return 422 for password shorter than 12 characters', async () => {
    const response = await request(app)
      .post('/api/auth/signup')
      .send({ ...validPayload, password: 'Short1!' });

    expect(response.status).toBe(422);
    expect(response.body).toEqual({ error: 'password_too_weak' });
  });

  test('should return 422 for password missing uppercase letter', async () => {
    const response = await request(app)
      .post('/api/auth/signup')
      .send({ ...validPayload, password: 'lowercase123!' });

    expect(response.status).toBe(422);
    expect(response.body).toEqual({ error: 'password_too_weak' });
  });

  test('should return 422 for password missing digit', async () => {
    const response = await request(app)
      .post('/api/auth/signup')
      .send({ ...validPayload, password: 'UppercasePass!' });

    expect(response.status).toBe(422);
    expect(response.body).toEqual({ error: 'password_too_weak' });
  });

  test('should return 422 for password missing special character', async () => {
    const response = await request(app)
      .post('/api/auth/signup')
      .send({ ...validPayload, password: 'UppercasePass123' });

    expect(response.status).toBe(422);
    expect(response.body).toEqual({ error: 'password_too_weak' });
  });

  test('should return 409 when email is already registered', async () => {
    // Setup: Create initial user
    await request(app).post('/api/auth/signup').send(validPayload);

    // Attempt to create again
    const response = await request(app)
      .post('/api/auth/signup')
      .send(validPayload);

    expect(response.status).toBe(409);
    expect(response.body).toEqual({ error: 'email_already_registered' });
  });
});
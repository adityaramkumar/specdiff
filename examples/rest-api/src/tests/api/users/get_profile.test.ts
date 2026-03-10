// generated_from: behaviors/users/profile
// spec_hash: d1f76ac9b12b1560185010f04ecae9a79ca4e17e78accdbabc8ee582b60bbd58
// generated_at: 2026-03-10T09:00:31.846844+00:00
// agent: testing-agent
import request from 'supertest';
import { app } from '../../app';

describe('GET /api/users/:id', () => {
  it('should return 401 when unauthenticated', async () => {
    const response = await request(app).get('/api/users/any-uuid');
    expect(response.status).toBe(401);
    expect(response.body).toEqual({ error: 'unauthorized' });
  });

  it('should return 200 and user profile when requesting own profile', async () => {
    const token = await loginUser('test@example.com', 'password');
    const userId = 'user-123';
    const response = await request(app)
      .get(`/api/users/${userId}`)
      .set('Authorization', `Bearer ${token}`);
      
    expect(response.status).toBe(200);
    expect(response.body).toEqual({
      id: expect.any(String),
      email: expect.any(String),
      name: expect.any(String),
      created_at: expect.stringMatching(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/)
    });
    expect(response.body).not.toHaveProperty('password_hash');
  });

  it('should return 403 when requesting another user profile', async () => {
    const token = await loginUser('test@example.com', 'password');
    const response = await request(app)
      .get('/api/users/different-user-id')
      .set('Authorization', `Bearer ${token}`);
    expect(response.status).toBe(403);
    expect(response.body).toEqual({ error: 'forbidden' });
  });

  it('should return 404 when user does not exist', async () => {
    const token = await loginUser('test@example.com', 'password');
    const response = await request(app)
      .get('/api/users/non-existent-id')
      .set('Authorization', `Bearer ${token}`);
    expect(response.status).toBe(404);
    expect(response.body).toEqual({ error: 'user_not_found' });
  });
});
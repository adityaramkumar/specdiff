// generated_from: behaviors/users/profile
// spec_hash: d1f76ac9b12b1560185010f04ecae9a79ca4e17e78accdbabc8ee582b60bbd58
// generated_at: 2026-03-10T09:00:31.846844+00:00
// agent: testing-agent
import request from 'supertest';
import { app } from '../../app';

describe('PUT /api/users/:id', () => {
  it('should update name successfully for own profile', async () => {
    const token = await loginUser('test@example.com', 'password');
    const response = await request(app)
      .put('/api/users/user-123')
      .set('Authorization', `Bearer ${token}`)
      .send({ name: 'New Name' });
      
    expect(response.status).toBe(200);
    expect(response.body.name).toBe('New Name');
  });

  it('should return 422 for empty name', async () => {
    const token = await loginUser('test@example.com', 'password');
    const response = await request(app)
      .put('/api/users/user-123')
      .set('Authorization', `Bearer ${token}`)
      .send({ name: '' });
      
    expect(response.status).toBe(422);
    expect(response.body).toEqual({ error: 'name_required' });
  });

  it('should return 422 for name longer than 100 characters', async () => {
    const token = await loginUser('test@example.com', 'password');
    const response = await request(app)
      .put('/api/users/user-123')
      .set('Authorization', `Bearer ${token}`)
      .send({ name: 'a'.repeat(101) });
      
    expect(response.status).toBe(422);
    expect(response.body).toEqual({ error: 'name_too_long' });
  });

  it('should return 403 when updating another user profile', async () => {
    const token = await loginUser('test@example.com', 'password');
    const response = await request(app)
      .put('/api/users/other-user-id')
      .set('Authorization', `Bearer ${token}`)
      .send({ name: 'Hacker' });
      
    expect(response.status).toBe(403);
    expect(response.body).toEqual({ error: 'forbidden' });
  });

  it('should not update email even if provided in payload', async () => {
    const token = await loginUser('test@example.com', 'password');
    const response = await request(app)
      .put('/api/users/user-123')
      .set('Authorization', `Bearer ${token}`)
      .send({ name: 'Valid Name', email: 'malicious@example.com' });
      
    expect(response.status).toBe(200);
    expect(response.body.email).toBe('test@example.com');
  });
});
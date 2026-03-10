// generated_from: behaviors/backend/crud
// spec_hash: 8b55d2dbbc650b7f723f46ef764d5ac1fcd143b6e5dd35a8812c4a3958f4c506
// generated_at: 2026-03-10T09:05:09.396168+00:00
// agent: testing-agent
import request from 'supertest';
import app from '../src/app';

describe('Todo CRUD API', () => {
  describe('POST /api/todos', () => {
    it('should create a todo successfully with 201', async () => {
      const response = await request(app).post('/api/todos').send({ title: 'Buy milk' });
      expect(response.status).toBe(201);
      expect(response.body).toMatchObject({
        title: 'Buy milk',
        completed: false
      });
      expect(response.body.id).toBeDefined();
      expect(new Date(response.body.created_at).getTime()).toBeLessThanOrEqual(Date.now());
    });

    it('should return 422 for empty or whitespace title', async () => {
      const response = await request(app).post('/api/todos').send({ title: ' ' });
      expect(response.status).toBe(422);
      expect(response.body).toEqual({ error: 'title_required' });
    });
  });

  describe('GET /api/todos', () => {
    it('should list todos sorted by created_at descending', async () => {
      await request(app).post('/api/todos').send({ title: 'First' });
      await request(app).post('/api/todos').send({ title: 'Second' });
      const response = await request(app).get('/api/todos');
      expect(response.status).toBe(200);
      expect(response.body.count).toBe(2);
      expect(new Date(response.body.todos[0].created_at).getTime()).toBeGreaterThan(new Date(response.body.todos[1].created_at).getTime());
    });

    it('should filter by completed status', async () => {
      const todo = await request(app).post('/api/todos').send({ title: 'Active' });
      await request(app).put(`/api/todos/${todo.body.id}`).send({ completed: true });
      
      const response = await request(app).get('/api/todos?completed=true');
      expect(response.body.todos.every((t: any) => t.completed === true)).toBe(true);
    });
  });

  describe('PUT /api/todos/:id', () => {
    it('should update title and completed status', async () => {
      const create = await request(app).post('/api/todos').send({ title: 'Original' });
      const id = create.body.id;
      const update = await request(app).put(`/api/todos/${id}`).send({ title: 'New', completed: true });
      expect(update.status).toBe(200);
      expect(update.body.title).toBe('New');
      expect(update.body.completed).toBe(true);
      expect(new Date(update.body.updated_at).getTime()).toBeGreaterThan(new Date(create.body.updated_at).getTime());
    });

    it('should return 200 with unchanged data when payload is empty', async () => {
      const create = await request(app).post('/api/todos').send({ title: 'Stay' });
      const update = await request(app).put(`/api/todos/${create.body.id}`).send({});
      expect(update.status).toBe(200);
      expect(update.body.title).toBe('Stay');
    });

    it('should return 404 for non-existent todo', async () => {
      const response = await request(app).put('/api/todos/non-existent').send({ title: 'Fail' });
      expect(response.status).toBe(404);
      expect(response.body).toEqual({ error: 'todo_not_found' });
    });
  });

  describe('DELETE /api/todos/:id', () => {
    it('should delete existing todo and return 204', async () => {
      const create = await request(app).post('/api/todos').send({ title: 'Delete me' });
      const del = await request(app).delete(`/api/todos/${create.body.id}`);
      expect(del.status).toBe(204);
    });

    it('should return 404 for non-existent todo delete', async () => {
      const response = await request(app).delete('/api/todos/non-existent');
      expect(response.status).toBe(404);
      expect(response.body).toEqual({ error: 'todo_not_found' });
    });
  });
});
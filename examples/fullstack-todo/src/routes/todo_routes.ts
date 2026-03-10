// generated_from: behaviors/backend/crud
// spec_hash: 8b55d2dbbc650b7f723f46ef764d5ac1fcd143b6e5dd35a8812c4a3958f4c506
// generated_at: 2026-03-10T09:05:09.387482+00:00
// agent: implementation-agent
import { Router } from 'express';
import { todoController } from '../controllers/todo_controller';

const router = Router();
router.get('/', todoController.list);
router.post('/', todoController.create);
router.put('/:id', todoController.update);
router.delete('/:id', todoController.delete);

export default router;
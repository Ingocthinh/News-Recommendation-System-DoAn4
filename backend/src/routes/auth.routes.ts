import { Router } from 'express';
import { register, login, getProfile } from '../controllers/auth.controller.js';
import { authMiddleware } from '../utils/auth.middleware.js';

const router = Router();

router.post('/register', register);
router.post('/login', login);
router.get('/profile', authMiddleware, getProfile);

export default router;

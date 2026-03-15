import { Router } from 'express';
import { logBehavior } from '../controllers/behavior.controller.js';

const router = Router();

router.post('/', logBehavior);

export default router;

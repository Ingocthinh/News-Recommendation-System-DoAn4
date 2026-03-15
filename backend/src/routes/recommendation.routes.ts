import { Router } from 'express';
import { getUserRecommendations, triggerTraining } from '../controllers/recommendation.controller.js';

const router = Router();

router.get('/:userId', getUserRecommendations);
router.post('/train', triggerTraining);

export default router;

import { Router } from 'express';
import newsRoutes from './news.routes.js';
import behaviorRoutes from './behavior.routes.js';
import recommendationRoutes from './recommendation.routes.js';
import authRoutes from './auth.routes.js';

const router = Router();

router.use('/auth', authRoutes);
router.use('/news', newsRoutes);
router.use('/behavior', behaviorRoutes);
router.use('/recommend', recommendationRoutes);

export default router;

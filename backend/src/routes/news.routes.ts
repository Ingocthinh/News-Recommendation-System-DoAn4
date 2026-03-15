import { Router } from 'express';
import { getLatestNews, getNewsByCategory, getNewsById, deleteAllNews, getNewsCount } from '../controllers/news.controller.js';

const router = Router();

router.get('/latest', getLatestNews);
router.get('/count', getNewsCount);
router.get('/category/:category', getNewsByCategory);
router.get('/:id', getNewsById);
router.delete('/all', deleteAllNews);

export default router;

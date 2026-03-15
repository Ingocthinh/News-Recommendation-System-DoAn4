import type { Request, Response } from 'express';
import prisma from '../services/db.service.js';
import axios from 'axios';

const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:5000';

export const getUserRecommendations = async (req: Request, res: Response) => {
    const { userId } = req.params;

    try {
        // 1. Try to get recommendations from ML service
        try {
            const response = await axios.get(`${ML_SERVICE_URL}/recommend/${userId}`);
            const recommendations = response.data; // Expected: [{ news_id: 1, score: 0.95 }, ...]

            const newsIds = recommendations.map((r: any) => parseInt(String(r.news_id)));
            const newsArticles = await prisma.news.findMany({
                where: { id: { in: newsIds } },
            });

            // Combine article data with scores
            const result = newsArticles.map(article => {
                // Find matching recommendation (handle potential string/number mismatch)
                const rec = recommendations.find((r: any) => 
                    String(r.news_id) === String(article.id)
                );
                return {
                    ...article,
                    score: rec ? rec.score : 0,
                };
            }).sort((a, b) => (b.score || 0) - (a.score || 0));


            return res.json(result);
        } catch (error: any) {
            console.warn('ML Service unreachable, falling back to latest news');
            console.error('ML Error Details:', error.message);
            if (error.response) {
                console.error('ML Error Response:', error.response.data);
            }
            const latestNews = await prisma.news.findMany({
                orderBy: { published_at: 'desc' },
                take: 10,
            });

            const fallbackResult = latestNews.map(article => ({
                ...article,
                score: Math.random() * (0.99 - 0.70) + 0.70, // Mock scores for UI consistency during development
            })).sort((a, b) => b.score - a.score);

            return res.json(fallbackResult);
        }
    } catch (error) {
        console.error('Error fetching recommendations:', error);
        res.status(500).json({ error: 'Failed to fetch recommendations' });
    }
};

export const triggerTraining = async (req: Request, res: Response) => {
    try {
        const response = await axios.post(`${ML_SERVICE_URL}/train-model`);
        res.json(response.data);
    } catch (error) {
        res.status(500).json({ error: 'Failed to trigger model training' });
    }
};

import type { Request, Response } from 'express';
import prisma from '../services/db.service.js';

export const getLatestNews = async (req: Request, res: Response) => {
    try {
        // Get distinct categories
        const categories = await prisma.news.findMany({
            select: { category: true },
            distinct: ['category'],
        });
        // Fetch latest articles from each category
        const allNews = await Promise.all(
            categories.map(c =>
                prisma.news.findMany({
                    where: { category: c.category },
                    orderBy: { published_at: 'desc' },
                    take: 8,
                })
            )
        );
        // Interleave: round-robin from each category
        const maxLen = Math.max(...allNews.map(a => a.length));
        const mixed: any[] = [];
        for (let i = 0; i < maxLen; i++) {
            for (const catArticles of allNews) {
                if (i < catArticles.length) mixed.push(catArticles[i]);
            }
        }
        res.json(mixed);
    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch news' });
    }
};

export const getNewsByCategory = async (req: Request, res: Response) => {
    const { category } = req.params;
    try {
        const news = await prisma.news.findMany({
            where: { category: category as string },
            orderBy: { published_at: 'desc' },
        });
        res.json(news);
    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch news by category' });
    }
};

export const getNewsById = async (req: Request, res: Response) => {
    const { id } = req.params;
    try {
        const article = await prisma.news.findUnique({
            where: { id: parseInt(id) },
        });
        if (!article) {
            return res.status(404).json({ error: 'News article not found' });
        }
        res.json(article);
    } catch (error) {
        res.status(500).json({ error: 'Failed to fetch article details' });
    }
};

export const deleteAllNews = async (req: Request, res: Response) => {
    try {
        // Xóa behaviors trước (foreign key constraint)
        const deletedBehaviors = await prisma.behavior.deleteMany({});
        // Xóa recommendations
        const deletedRecs = await prisma.recommendation.deleteMany({});
        // Xóa tất cả news
        const deletedNews = await prisma.news.deleteMany({});

        res.json({
            message: 'Đã xóa toàn bộ dữ liệu',
            deleted: {
                news: deletedNews.count,
                behaviors: deletedBehaviors.count,
                recommendations: deletedRecs.count,
            }
        });
    } catch (error) {
        console.error('Error deleting all news:', error);
        res.status(500).json({ error: 'Failed to delete news' });
    }
};

export const getNewsCount = async (req: Request, res: Response) => {
    try {
        const count = await prisma.news.count();
        const categories = await prisma.news.groupBy({
            by: ['category'],
            _count: { id: true },
        });
        res.json({ total: count, by_category: categories });
    } catch (error) {
        res.status(500).json({ error: 'Failed to get news count' });
    }
};

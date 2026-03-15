import type { Request, Response } from 'express';
import prisma from '../services/db.service.js';
import axios from 'axios';

const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://localhost:5000';

export const logBehavior = async (req: Request, res: Response) => {
    const { user_id, news_id, action, dwell_time } = req.body;

    if (!user_id || !news_id || !action) {
        return res.status(400).json({ error: 'Missing required fields: user_id, news_id, action' });
    }

    try {
        // 1. Save to Database
        let user = await prisma.user.findUnique({ where: { id: user_id } });
        if (!user) {
            user = await prisma.user.create({ data: { id: user_id, username: `user_${user_id}` } });
        }

        const behavior = await prisma.behavior.create({
            data: {
                user_id,
                news_id,
                action,
                dwell_time: dwell_time ? parseInt(dwell_time) : 0
            },
        });

        // 2. Sync with ML Service for Real-time Updates
        try {
            await axios.post(`${ML_SERVICE_URL}/record-action`, {
                user_id,
                news_id,
                action,
                dwell_time: dwell_time || 0
            });
            console.log(`Synced behavior to ML Service: ${user_id} -> ${news_id}`);
        } catch (mlError) {
            console.error('Failed to sync behavior to ML Service:', mlError.message);
            // Non-blocking error
        }

        res.status(201).json(behavior);
    } catch (error) {
        console.error('Error logging behavior:', error);
        res.status(500).json({ error: 'Failed to log behavior' });
    }
};

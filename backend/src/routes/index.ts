import { Express } from 'express';
import { authRoutes } from './auth';
import { chatRoutes } from './chat';
import { reportRoutes } from './reports';
import { financialDataRoutes } from './financialData';

export function setupRoutes(app: Express): void {
  // API routes
  app.use('/api/auth', authRoutes);
  app.use('/api/chat', chatRoutes);
  app.use('/api/reports', reportRoutes);
  app.use('/api/financial-data', financialDataRoutes);

  // Health check
  app.get('/api/health', (req, res) => {
    res.json({
      success: true,
      message: 'Financial Assistant API is running',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    });
  });

  // 404 handler
  app.use('*', (req, res) => {
    res.status(404).json({
      success: false,
      error: 'Route not found',
      path: req.originalUrl,
    });
  });
}

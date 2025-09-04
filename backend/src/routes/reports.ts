import { Router, Request, Response } from 'express';
import { reportService } from '../services/index';
import { asyncHandler, createError } from '../middleware/errorHandler';

const router = Router();

// Generate report
router.post('/generate', asyncHandler(async (req: Request, res: Response) => {
  const { conversationId, clientName, preferences } = req.body;

  if (!conversationId || !clientName) {
    throw createError('Conversation ID and client name are required', 400);
  }

  const report = await reportService.generateReport(conversationId, clientName, preferences);

  res.json({
    success: true,
    report,
  });
}));

// Get report by ID
router.get('/:reportId', asyncHandler(async (req: Request, res: Response) => {
  const { reportId } = req.params;

  const report = reportService.getReport(reportId);
  if (!report) {
    throw createError('Report not found', 404);
  }

  res.json({
    success: true,
    report,
  });
}));

// Get all reports
router.get('/', asyncHandler(async (req: Request, res: Response) => {
  const reports = reportService.getAllReports();

  res.json({
    success: true,
    reports,
  });
}));

// Delete report
router.delete('/:reportId', asyncHandler(async (req: Request, res: Response) => {
  const { reportId } = req.params;

  const deleted = reportService.deleteReport(reportId);
  if (!deleted) {
    throw createError('Report not found', 404);
  }

  res.json({
    success: true,
    message: 'Report deleted successfully',
  });
}));

export { router as reportRoutes };

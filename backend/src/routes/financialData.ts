import { Router, Request, Response } from 'express';
import { memoryManager } from '../services/index';
import { asyncHandler, createError } from '../middleware/errorHandler';

const router = Router();

// Get financial data for a conversation
router.get('/:conversationId', asyncHandler(async (req: Request, res: Response) => {
  const { conversationId } = req.params;
  const { client_name } = req.query;

  if (!conversationId) {
    throw createError('Conversation ID is required', 400);
  }

  if (!client_name || typeof client_name !== 'string') {
    throw createError('Client name is required', 400);
  }

  console.log(`🔍 Fetching financial data for conversation: ${conversationId}, client: ${client_name}`);

  try {
    const financialData = await memoryManager.generateFinancialDataFromConversation(
      conversationId,
      client_name
    );

    res.json({
      success: true,
      financial_data: financialData,
      conversationId,
      clientName: client_name,
    });
  } catch (error) {
    console.error('❌ Error fetching financial data:', error);
    throw createError('Failed to fetch financial data', 500);
  }
}));

export { router as financialDataRoutes };

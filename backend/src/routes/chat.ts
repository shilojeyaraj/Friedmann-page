import { Router, Request, Response } from 'express';
import { googleAI } from '../services/index';
import { memoryManager } from '../services/index';
import { asyncHandler, createError } from '../middleware/errorHandler';

const router = Router();

// Chat endpoint
router.post('/', asyncHandler(async (req: Request, res: Response) => {
  const { message, conversationId, clientName } = req.body;

  if (!message || typeof message !== 'string') {
    throw createError('Message is required', 400);
  }

  if (!conversationId || typeof conversationId !== 'string') {
    throw createError('Conversation ID is required', 400);
  }

  const model = googleAI.getGenerativeModel({ model: 'gemini-pro' });

  try {
    // Add user message to memory
    await memoryManager.addMessage(conversationId, 'user', message);

    // Generate AI response
    const prompt = `
      You are a professional financial advisor. Respond to the client's message in a helpful, informative, and professional manner.
      
      Client: ${clientName || 'Client'}
      Message: ${message}
      
      Please provide a thoughtful response that addresses their financial concerns or questions.
      Keep your response concise but comprehensive.
    `;

    const result = await model.generateContent(prompt);
    const response = result.response.text();

    // Add AI response to memory
    await memoryManager.addMessage(conversationId, 'assistant', response);

    res.json({
      success: true,
      message: {
        content: response,
        citations: [],
      },
      conversationId,
    });
  } catch (error) {
    console.error('❌ Error in chat endpoint:', error);
    throw createError('Failed to process chat message', 500);
  }
}));

// Search conversations
router.post('/search', asyncHandler(async (req: Request, res: Response) => {
  const { query, conversationId, limit = 5 } = req.body;

  if (!query || typeof query !== 'string') {
    throw createError('Query is required', 400);
  }

  const results = await memoryManager.searchConversations(query, conversationId, limit);

  res.json({
    success: true,
    results,
    query,
    totalFound: results.length,
  });
}));

// Get conversation summary
router.get('/summary/:conversationId', asyncHandler(async (req: Request, res: Response) => {
  const { conversationId } = req.params;

  if (!conversationId) {
    throw createError('Conversation ID is required', 400);
  }

  const summary = await memoryManager.getConversationSummary(conversationId);
  const history = await memoryManager.getConversationHistory(conversationId);

  res.json({
    success: true,
    conversationId,
    summary,
    messageCount: history.length,
    lastUpdated: new Date().toISOString(),
  });
}));

export { router as chatRoutes };

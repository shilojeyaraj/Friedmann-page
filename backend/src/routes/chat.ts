import { Router, Request, Response } from 'express';
import { openai } from '../services/index';
import { memoryManager } from '../services/index';
import { asyncHandler, createError } from '../middleware/errorHandler';

const router = Router();

// Chat endpoint
router.post('/', asyncHandler(async (req: Request, res: Response) => {
  const { message, conversationId, conversation_id, clientName } = req.body;

  // Log incoming request
  console.log('📨 Incoming chat request:', {
    message: message?.substring(0, 100) + (message?.length > 100 ? '...' : ''),
    conversationId: conversationId || conversation_id,
    clientName,
    timestamp: new Date().toISOString()
  });

  if (!message || typeof message !== 'string') {
    throw createError('Message is required', 400);
  }

  // Support both conversationId and conversation_id for compatibility
  const actualConversationId = conversationId || conversation_id;
  if (!actualConversationId || typeof actualConversationId !== 'string') {
    throw createError('Conversation ID is required', 400);
  }

  try {
    // Add user message to memory
    await memoryManager.addMessage(actualConversationId, 'user', message);

    // Generate AI response
    const messages = [
      {
        role: 'system' as const,
        content: `You are a professional financial advisor. Respond to the client's message in a helpful, informative, and professional manner. Keep your response concise but comprehensive.`
      },
      {
        role: 'user' as const,
        content: `Client: ${clientName || 'Client'}\nMessage: ${message}`
      }
    ];

    console.log('🤖 Generating AI response...');
    const completion = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: messages,
      max_tokens: 1000,
      temperature: 0.7,
    });
    
    const response = completion.choices[0]?.message?.content || 'I apologize, but I could not generate a response.';

    // Log AI response
    console.log('🤖 AI Response:', {
      content: response.substring(0, 100) + (response.length > 100 ? '...' : ''),
      conversationId: actualConversationId,
      timestamp: new Date().toISOString()
    });

    // Add AI response to memory
    await memoryManager.addMessage(actualConversationId, 'assistant', response);

    res.json({
      success: true,
      message: {
        content: response,
        citations: [],
      },
      conversationId: actualConversationId,
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

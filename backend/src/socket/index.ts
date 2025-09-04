import { Server as SocketIOServer } from 'socket.io';
import { googleAI } from '../services/index';
import { memoryManager } from '../services/index';

export function setupSocketHandlers(io: SocketIOServer): void {
  io.on('connection', (socket) => {
    console.log(`🔌 Client connected: ${socket.id}`);

    socket.on('message', async (data) => {
      try {
        const { message, conversationId, clientName } = data;

        if (!message || !conversationId) {
          socket.emit('error', { message: 'Message and conversation ID are required' });
          return;
        }

        // Add user message to memory
        await memoryManager.addMessage(conversationId, 'user', message);

        // Generate AI response
        const model = googleAI.getGenerativeModel({ model: 'gemini-pro' });
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

        // Send response back to client
        socket.emit('response', {
          message: response,
          conversationId,
          timestamp: new Date().toISOString(),
        });
      } catch (error) {
        console.error('❌ Error in socket message handler:', error);
        socket.emit('error', { message: 'Failed to process message' });
      }
    });

    socket.on('disconnect', () => {
      console.log(`🔌 Client disconnected: ${socket.id}`);
    });
  });
}

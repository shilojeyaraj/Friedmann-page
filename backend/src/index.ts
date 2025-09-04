import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import morgan from 'morgan';
import dotenv from 'dotenv';
import { createServer } from 'http';
import { Server as SocketIOServer } from 'socket.io';
import { initializeServices } from './services';
import { setupRoutes } from './routes';
import { setupSocketHandlers } from './socket';
import { errorHandler } from './middleware/errorHandler';
import { rateLimiter } from './middleware/rateLimiter';

// Load environment variables
dotenv.config();

const app = express();
const server = createServer(app);
const io = new SocketIOServer(server, {
  cors: {
    origin: process.env.FRONTEND_URL || "http://localhost:3000",
    methods: ["GET", "POST"]
  }
});

const PORT = process.env.PORT || 8000;

// Middleware
app.use(helmet());
app.use(compression());
app.use(morgan('combined'));
app.use(cors({
  origin: process.env.FRONTEND_URL || "http://localhost:3000",
  credentials: true
}));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Rate limiting
app.use(rateLimiter);

// Initialize services
initializeServices()
  .then(() => {
    console.log('✅ All services initialized successfully');
    
    // Setup routes
    setupRoutes(app);
    
    // Setup socket handlers
    setupSocketHandlers(io);
    
    // Error handling middleware (must be last)
    app.use(errorHandler);
    
    // Start server
    server.listen(PORT, () => {
      console.log(`🚀 Financial Assistant API running on port ${PORT}`);
      console.log(`🌐 Server: http://localhost:${PORT}`);
      console.log(`🔌 WebSocket support enabled`);
      console.log(`🔑 API Key Status: ${process.env.GOOGLE_API_KEY ? '✅ Configured' : '❌ Missing'}`);
    });
  })
  .catch((error) => {
    console.error('❌ Failed to initialize services:', error);
    process.exit(1);
  });

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('🛑 SIGTERM received, shutting down gracefully');
  server.close(() => {
    console.log('✅ Process terminated');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('🛑 SIGINT received, shutting down gracefully');
  server.close(() => {
    console.log('✅ Process terminated');
    process.exit(0);
  });
});

export { app, server, io };

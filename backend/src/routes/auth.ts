import { Router, Request, Response } from 'express';
import { AuthService } from '../services/authService';
import { emailService } from '../services/index';
import { asyncHandler, createError } from '../middleware/errorHandler';

const router = Router();
const authService = new AuthService();

// Request access by submitting email
router.post('/request-access', asyncHandler(async (req: Request, res: Response) => {
  const { email } = req.body;

  if (!email || typeof email !== 'string') {
    throw createError('Email is required', 400);
  }

  const normalizedEmail = email.trim().toLowerCase();

  // Check if email is authorized
  const isAuthorized = await authService.isClientAuthorized(normalizedEmail);
  if (!isAuthorized) {
    return res.status(403).json({
      success: false,
      error: 'Email not authorized. Please contact your financial advisor.',
    });
  }

  // Generate passcode
  const passcode = authService.generatePasscode();
  const expiresAt = new Date(Date.now() + 15 * 60 * 1000); // 15 minutes

  // Store token in database
  const ipAddress = req.ip;
  const userAgent = req.get('User-Agent');

  const tokenStored = await authService.storeAuthToken(
    normalizedEmail,
    passcode,
    expiresAt,
    ipAddress,
    userAgent
  );

  if (!tokenStored) {
    throw createError('Failed to store authorization token', 500);
  }

  // Send email
  const emailSent = await emailService.sendPasscodeEmail(normalizedEmail, passcode);
  if (!emailSent) {
    throw createError('Failed to send passcode email', 500);
  }

  res.json({
    success: true,
    message: 'Passcode sent to your email',
    email: normalizedEmail,
  });
}));

// Verify passcode and create session
router.post('/verify-token', asyncHandler(async (req: Request, res: Response) => {
  const { email, token } = req.body;

  if (!email || !token) {
    throw createError('Email and token are required', 400);
  }

  const normalizedEmail = email.trim().toLowerCase();
  const normalizedToken = token.trim();

  // Verify token
  const isValid = await authService.verifyAuthToken(normalizedEmail, normalizedToken);
  if (!isValid) {
    return res.status(401).json({
      success: false,
      error: 'Invalid or expired passcode',
    });
  }

  // Create session
  const sessionToken = await authService.createClientSession(normalizedEmail);
  if (!sessionToken) {
    throw createError('Failed to create session', 500);
  }

  res.json({
    success: true,
    message: 'Access granted',
    sessionToken,
    email: normalizedEmail,
  });
}));

// Validate current session
router.get('/validate-session', asyncHandler(async (req: Request, res: Response) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ authenticated: false });
  }

  const sessionToken = authHeader.substring(7);
  const email = await authService.verifyClientSession(sessionToken);

  if (!email) {
    return res.status(401).json({ authenticated: false });
  }

  res.json({
    authenticated: true,
    email,
  });
}));

// Logout and clear session
router.post('/logout', asyncHandler(async (req: Request, res: Response) => {
  const authHeader = req.headers.authorization;
  if (authHeader && authHeader.startsWith('Bearer ')) {
    const sessionToken = authHeader.substring(7);
    await authService.logoutClient(sessionToken);
  }

  res.json({
    success: true,
    message: 'Logged out successfully',
  });
}));

export { router as authRoutes };

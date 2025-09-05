import { GoogleGenerativeAI } from '@google/generative-ai';
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { EmailService } from './emailService';
import { MemoryManager } from './memoryManager';
import { ReportService } from './reportService';

// Global service instances
export let googleAI: GoogleGenerativeAI;
export let supabase: SupabaseClient | null = null;
export let emailService: EmailService;
export let memoryManager: MemoryManager;
export let reportService: ReportService;

export async function initializeServices(): Promise<void> {
  console.log('🔄 Initializing services...');

  // Initialize Google Gemini
  if (!process.env['GOOGLE_API_KEY']) {
    throw new Error('GOOGLE_API_KEY environment variable is required');
  }
  
  googleAI = new GoogleGenerativeAI(process.env['GOOGLE_API_KEY']);
  console.log('✅ Google Gemini initialized successfully');

  // Initialize Supabase
  if (process.env['SUPABASE_URL'] && process.env['SUPABASE_KEY']) {
    supabase = createClient(process.env['SUPABASE_URL'], process.env['SUPABASE_KEY']);
    console.log('✅ Supabase initialized successfully');
  } else {
    console.log('⚠️ SUPABASE_URL or SUPABASE_KEY not found in environment variables');
  }

  // Initialize Email Service
  emailService = new EmailService();
  if (emailService.isConfigured()) {
    console.log('✅ Email service configured successfully');
  } else {
    console.log('⚠️ Email service not configured - SMTP credentials missing');
  }

  // Initialize Memory Manager
  memoryManager = new MemoryManager();
  console.log('✅ LangChain memory manager initialized');

  // Initialize Report Service
  reportService = new ReportService();
  console.log('✅ Report service initialized');

  console.log('🎉 All services initialized successfully');
}

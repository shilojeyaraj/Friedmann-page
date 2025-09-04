import { supabase } from './index';
import { v4 as uuidv4 } from 'uuid';
import { DateTime } from 'luxon';

export interface AuthToken {
  id: string;
  email: string;
  token: string;
  expiresAt: Date;
  used: boolean;
  createdAt: Date;
  ipAddress?: string;
  userAgent?: string;
}

export interface ClientSession {
  id: string;
  email: string;
  sessionToken: string;
  expiresAt: Date;
  createdAt: Date;
  lastAccessed: Date;
}

export class AuthService {
  public async isClientAuthorized(email: string): Promise<boolean> {
    if (!supabase) {
      console.log('⚠️ Supabase not available');
      return false;
    }

    try {
      const { data, error } = await supabase
        .from('clients')
        .select('*')
        .eq('email', email.toLowerCase())
        .eq('is_active', true);

      if (error) {
        console.error('❌ Error checking client authorization:', error);
        return false;
      }

      return data && data.length > 0;
    } catch (error) {
      console.error('❌ Error checking client authorization:', error);
      return false;
    }
  }

  public generatePasscode(length: number = 6): string {
    return Math.floor(100000 + Math.random() * 900000).toString();
  }

  public async storeAuthToken(
    email: string,
    token: string,
    expiresAt: Date,
    ipAddress?: string,
    userAgent?: string
  ): Promise<boolean> {
    if (!supabase) {
      return false;
    }

    try {
      const { error } = await supabase
        .from('authorization_tokens')
        .insert({
          email: email.toLowerCase(),
          token,
          expires_at: expiresAt.toISOString(),
          ip_address: ipAddress,
          user_agent: userAgent,
        });

      if (error) {
        console.error('❌ Error storing auth token:', error);
        return false;
      }

      return true;
    } catch (error) {
      console.error('❌ Error storing auth token:', error);
      return false;
    }
  }

  public async verifyAuthToken(email: string, token: string): Promise<boolean> {
    if (!supabase) {
      return false;
    }

    try {
      const now = new Date();
      
      const { data, error } = await supabase
        .from('authorization_tokens')
        .select('*')
        .eq('email', email.toLowerCase())
        .eq('token', token)
        .eq('used', false);

      if (error) {
        console.error('❌ Error verifying auth token:', error);
        return false;
      }

      if (!data || data.length === 0) {
        return false;
      }

      const tokenData = data[0];
      const expiresAt = new Date(tokenData.expires_at);

      if (now > expiresAt) {
        return false;
      }

      // Mark token as used
      await supabase
        .from('authorization_tokens')
        .update({ used: true })
        .eq('id', tokenData.id);

      return true;
    } catch (error) {
      console.error('❌ Error verifying auth token:', error);
      return false;
    }
  }

  public async createClientSession(email: string): Promise<string | null> {
    if (!supabase) {
      return null;
    }

    try {
      const sessionToken = uuidv4();
      const expiresAt = DateTime.now().plus({ hours: 24 }).toJSDate();

      const { error } = await supabase
        .from('client_sessions')
        .insert({
          email: email.toLowerCase(),
          session_token: sessionToken,
          expires_at: expiresAt.toISOString(),
        });

      if (error) {
        console.error('❌ Error creating client session:', error);
        return null;
      }

      return sessionToken;
    } catch (error) {
      console.error('❌ Error creating client session:', error);
      return null;
    }
  }

  public async verifyClientSession(sessionToken: string): Promise<string | null> {
    if (!supabase) {
      return null;
    }

    try {
      const { data, error } = await supabase
        .from('client_sessions')
        .select('*')
        .eq('session_token', sessionToken);

      if (error) {
        console.error('❌ Error verifying client session:', error);
        return null;
      }

      if (!data || data.length === 0) {
        return null;
      }

      const sessionData = data[0];
      const expiresAt = new Date(sessionData.expires_at);

      if (new Date() > expiresAt) {
        return null;
      }

      // Update last accessed time
      await supabase
        .from('client_sessions')
        .update({ last_accessed: new Date().toISOString() })
        .eq('id', sessionData.id);

      return sessionData.email;
    } catch (error) {
      console.error('❌ Error verifying client session:', error);
      return null;
    }
  }

  public async logoutClient(sessionToken: string): Promise<boolean> {
    if (!supabase) {
      return false;
    }

    try {
      const { error } = await supabase
        .from('client_sessions')
        .delete()
        .eq('session_token', sessionToken);

      if (error) {
        console.error('❌ Error logging out client:', error);
        return false;
      }

      return true;
    } catch (error) {
      console.error('❌ Error logging out client:', error);
      return false;
    }
  }

  public async cleanupExpiredTokens(): Promise<void> {
    if (!supabase) {
      return;
    }

    try {
      const now = new Date().toISOString();
      
      await supabase
        .from('authorization_tokens')
        .delete()
        .or(`expires_at.lt.${now},used.eq.true`);
    } catch (error) {
      console.error('❌ Error cleaning up expired tokens:', error);
    }
  }

  public async cleanupExpiredSessions(): Promise<void> {
    if (!supabase) {
      return;
    }

    try {
      const now = new Date().toISOString();
      
      await supabase
        .from('client_sessions')
        .delete()
        .lt('expires_at', now);
    } catch (error) {
      console.error('❌ Error cleaning up expired sessions:', error);
    }
  }
}

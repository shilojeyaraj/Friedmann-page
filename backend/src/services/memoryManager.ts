import { GoogleGenerativeAI } from '@google/generative-ai';
import { GoogleGenerativeAIEmbeddings } from '@langchain/google-genai';
import { Chroma } from '@langchain/community/vectorstores/chroma';
import { RecursiveCharacterTextSplitter } from 'langchain/text_splitter';
import { HumanMessage, AIMessage } from '@langchain/core/messages';
import { googleAI } from './index';

export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export class MemoryManager {
  private vectorstore: Chroma;
  private textSplitter: RecursiveCharacterTextSplitter;
  private conversationHistories: Map<string, ConversationMessage[]> = new Map();
  private conversationSummaries: Map<string, string> = new Map();
  private pendingUserMessages: Map<string, string> = new Map();

  constructor() {
    // Initialize embeddings
    const embeddings = new GoogleGenerativeAIEmbeddings({
      model: 'models/embedding-001',
      apiKey: process.env.GOOGLE_API_KEY!,
    });

    // Initialize vector store
    this.vectorstore = new Chroma(embeddings, {
      collectionName: 'financial_conversations',
    });

    // Initialize text splitter
    this.textSplitter = new RecursiveCharacterTextSplitter({
      chunkSize: 1000,
      chunkOverlap: 200,
    });
  }

  public async addMessage(conversationId: string, role: 'user' | 'assistant', message: string): Promise<void> {
    console.log(`🔍 Adding message to conversation ${conversationId}: ${role} - ${message.substring(0, 50)}...`);

    // Store the message in conversation history
    if (!this.conversationHistories.has(conversationId)) {
      this.conversationHistories.set(conversationId, []);
    }

    const conversationHistory = this.conversationHistories.get(conversationId)!;
    conversationHistory.push({
      role,
      content: message,
      timestamp: new Date(),
    });

    // If it's a user message, store it temporarily
    if (role === 'user') {
      this.pendingUserMessages.set(conversationId, message);
      console.log(`📝 Stored pending user message for conversation ${conversationId}`);
    }

    // If it's an assistant message, process the full conversation context
    if (role === 'assistant') {
      const userMessage = this.pendingUserMessages.get(conversationId);
      if (userMessage) {
        // Create documents for vector store
        const userDoc = new HumanMessage(userMessage);
        const assistantDoc = new AIMessage(message);
        
        // Add to vector store
        await this.vectorstore.addDocuments([
          {
            pageContent: userDoc.content,
            metadata: {
              conversationId,
              role: 'user',
              timestamp: new Date().toISOString(),
            },
          },
          {
            pageContent: assistantDoc.content,
            metadata: {
              conversationId,
              role: 'assistant',
              timestamp: new Date().toISOString(),
            },
          },
        ]);

        // Clear pending message
        this.pendingUserMessages.delete(conversationId);
        console.log(`✅ Added conversation context to vector store for ${conversationId}`);
      }
    }
  }

  public async getConversationHistory(conversationId: string): Promise<ConversationMessage[]> {
    return this.conversationHistories.get(conversationId) || [];
  }

  public async searchConversations(query: string, conversationId?: string, limit: number = 5): Promise<any[]> {
    try {
      const searchResults = await this.vectorstore.similaritySearch(query, limit, {
        conversationId: conversationId,
      });

      return searchResults.map(result => ({
        content: result.pageContent,
        metadata: result.metadata,
        score: (result as any).score,
      }));
    } catch (error) {
      console.error('❌ Error searching conversations:', error);
      return [];
    }
  }

  public async getConversationSummary(conversationId: string): Promise<string> {
    if (this.conversationSummaries.has(conversationId)) {
      return this.conversationSummaries.get(conversationId)!;
    }

    const history = await this.getConversationHistory(conversationId);
    if (history.length === 0) {
      this.conversationSummaries.set(conversationId, "No conversation history yet.");
      return "No conversation history yet.";
    }

    try {
      const model = googleAI.getGenerativeModel({ model: 'gemini-pro' });
      const conversationText = history
        .map(msg => `${msg.role}: ${msg.content}`)
        .join('\n');

      const prompt = `Please provide a concise summary of this financial conversation:\n\n${conversationText}`;
      const result = await model.generateContent(prompt);
      const summary = result.response.text();

      this.conversationSummaries.set(conversationId, summary);
      return summary;
    } catch (error) {
      console.error('❌ Error generating conversation summary:', error);
      this.conversationSummaries.set(conversationId, "Error generating summary.");
      return "Error generating summary.";
    }
  }

  public async generateFinancialDataFromConversation(conversationId: string, clientName: string): Promise<any> {
    try {
      console.log(`🔍 Generating financial data for conversation: ${conversationId}, client: ${clientName}`);

      const history = await this.getConversationHistory(conversationId);
      if (history.length === 0) {
        console.log('⚠️ No conversation history found');
        return this.getDefaultFinancialData();
      }

      // Extract conversation text
      const conversationText = history
        .map(msg => `${msg.role}: ${msg.content}`)
        .join('\n');

      console.log(`🔍 Conversation text extracted: ${conversationText.substring(0, 200)}...`);

      const model = googleAI.getGenerativeModel({ model: 'gemini-pro' });
      const prompt = `
        Analyze this financial conversation and extract structured financial data. 
        Only use information explicitly mentioned in the conversation. Do not add any fictional data.
        
        Conversation:
        ${conversationText}
        
        Client: ${clientName}
        
        Please return a JSON object with this structure:
        {
          "assets": {
            "rrsp": number,
            "tfsa": number,
            "investments": number,
            "realEstate": number
          },
          "liabilities": {
            "mortgage": number,
            "creditCard": number,
            "loans": number
          },
          "goals": {
            "retirement": number,
            "education": number,
            "emergency": number
          }
        }
        
        If no specific amounts are mentioned, use 0 for those fields.
      `;

      const result = await model.generateContent(prompt);
      const responseText = result.response.text();
      
      // Try to parse JSON from response
      const jsonMatch = responseText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        const financialData = JSON.parse(jsonMatch[0]);
        console.log(`✅ Generated financial data:`, financialData);
        return financialData;
      } else {
        console.log('⚠️ Could not parse JSON from response, using default data');
        return this.getDefaultFinancialData();
      }
    } catch (error) {
      console.error('❌ Error generating financial data from conversation:', error);
      return this.getDefaultFinancialData();
    }
  }

  private getDefaultFinancialData(): any {
    return {
      assets: {
        rrsp: 0,
        tfsa: 0,
        investments: 0,
        realEstate: 0,
      },
      liabilities: {
        mortgage: 0,
        creditCard: 0,
        loans: 0,
      },
      goals: {
        retirement: 0,
        education: 0,
        emergency: 0,
      },
    };
  }
}

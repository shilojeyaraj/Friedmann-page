import { OpenAIEmbeddings } from '@langchain/openai';
import { Chroma } from '@langchain/community/vectorstores/chroma';
import { HumanMessage, AIMessage } from '@langchain/core/messages';
import { openai } from './index';

export interface ConversationMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export class MemoryManager {
  private vectorstore: Chroma;
  private conversationHistories: Map<string, ConversationMessage[]> = new Map();
  private conversationSummaries: Map<string, string> = new Map();
  private pendingUserMessages: Map<string, string> = new Map();

  constructor() {
    // Initialize embeddings
    const embeddings = new OpenAIEmbeddings({
      openAIApiKey: process.env['OPENAI_API_KEY']!,
    });

    // Initialize vector store
    this.vectorstore = new Chroma(embeddings, {
      collectionName: 'financial_conversations',
    });

    // Text splitter removed as it's not used in this implementation
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
            pageContent: typeof userDoc.content === 'string' ? userDoc.content : JSON.stringify(userDoc.content),
            metadata: {
              conversationId,
              role: 'user',
              timestamp: new Date().toISOString(),
            },
          },
          {
            pageContent: typeof assistantDoc.content === 'string' ? assistantDoc.content : JSON.stringify(assistantDoc.content),
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
      const conversationText = history
        .map(msg => `${msg.role}: ${msg.content}`)
        .join('\n');

      const completion = await openai.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [
          {
            role: 'system',
            content: 'You are a helpful assistant that summarizes financial conversations concisely.'
          },
          {
            role: 'user',
            content: `Please provide a concise summary of this financial conversation:\n\n${conversationText}`
          }
        ],
        max_tokens: 500,
        temperature: 0.3,
      });
      
      const summary = completion.choices[0]?.message?.content || 'Unable to generate summary';

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

      const completion = await openai.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [
          {
            role: 'system',
            content: 'You are a financial data extraction assistant. Analyze conversations and extract structured financial data. Only use information explicitly mentioned. Return valid JSON only.'
          },
          {
            role: 'user',
            content: `
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
            `
          }
        ],
        max_tokens: 1500,
        temperature: 0.1,
      });
      
      const responseText = completion.choices[0]?.message?.content || '{}';
      
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

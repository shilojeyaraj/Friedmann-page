import { openai } from './index';
import { memoryManager } from './index';
import { DateTime } from 'luxon';

export interface FinancialData {
  assets: {
    rrsp: number;
    tfsa: number;
    investments: number;
    realEstate: number;
  };
  liabilities: {
    mortgage: number;
    creditCard: number;
    loans: number;
  };
  goals: {
    retirement: number;
    education: number;
    emergency: number;
  };
}

export interface ReportData {
  id: string;
  clientName: string;
  conversationId: string;
  content: string;
  financialData: FinancialData;
  createdAt: Date;
  updatedAt: Date;
}

export class ReportService {
  private reports: Map<string, ReportData> = new Map();

  public async generateReport(
    conversationId: string,
    clientName: string,
    preferences?: string
  ): Promise<ReportData> {
    try {
      console.log(`🔍 Generating report for conversation: ${conversationId}, client: ${clientName}`);

      // Get financial data from conversation
      const financialData = await memoryManager.generateFinancialDataFromConversation(
        conversationId,
        clientName
      );

      // Get conversation history for context
      const history = await memoryManager.getConversationHistory(conversationId);
      const conversationText = history
        .map(msg => `${msg.role}: ${msg.content}`)
        .join('\n');

      // Generate report content
      const reportContent = await this.generateReportContent(
        clientName,
        conversationText,
        financialData,
        preferences
      );

      // Create report data
      const reportId = `report_${conversationId}_${Date.now()}`;
      const reportData: ReportData = {
        id: reportId,
        clientName,
        conversationId,
        content: reportContent,
        financialData,
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      // Store report
      this.reports.set(reportId, reportData);

      console.log(`✅ Report generated successfully: ${reportId}`);
      return reportData;
    } catch (error) {
      console.error('❌ Error generating report:', error);
      throw error;
    }
  }

  private async generateReportContent(
    clientName: string,
    conversationText: string,
    financialData: FinancialData,
    preferences?: string
  ): Promise<string> {
    try {
      const completion = await openai.chat.completions.create({
        model: 'gpt-4o-mini',
        messages: [
          {
            role: 'system',
            content: 'You are a professional financial advisor who creates comprehensive financial reports. Generate detailed, actionable reports based on client conversations and financial data. Format responses in markdown with clear headings and bullet points.'
          },
          {
            role: 'user',
            content: `
              Generate a comprehensive financial report for ${clientName} based on the following conversation and financial data.
              
              ${preferences ? `Client Preferences: ${preferences}` : ''}
              
              Conversation History:
              ${conversationText}
              
              Financial Data:
              ${JSON.stringify(financialData, null, 2)}
              
              Please create a detailed financial report with the following sections:
              1. Executive Summary
              2. Financial Health Assessment
              3. Recommended Investment Strategy
              4. Risk Analysis
              5. Retirement Planning
              6. Tax Optimization Opportunities
              7. Action Items and Next Steps
              
              Make the report professional, detailed, and actionable. Use only information from the conversation and financial data provided.
              Format the response in markdown with clear headings and bullet points.
            `
          }
        ],
        max_tokens: 2000,
        temperature: 0.7,
      });

      return completion.choices[0]?.message?.content || 'Unable to generate report';
    } catch (error) {
      console.error('❌ Error generating report content:', error);
      return this.getDefaultReportContent(clientName);
    }
  }

  private getDefaultReportContent(clientName: string): string {
    return `
# Financial Report for ${clientName}

## Executive Summary
This report provides a comprehensive analysis of your financial situation based on our recent conversation.

## Financial Health Assessment
- **Assets**: Please provide detailed information about your current assets
- **Liabilities**: Please provide information about your current debts and obligations
- **Net Worth**: Calculated based on assets minus liabilities

## Recommended Investment Strategy
Based on your financial goals and risk tolerance, we recommend:
- Diversified portfolio approach
- Regular contribution strategy
- Risk management considerations

## Risk Analysis
- Market risk assessment
- Personal risk factors
- Mitigation strategies

## Retirement Planning
- Current retirement savings analysis
- Projected retirement needs
- Contribution recommendations

## Tax Optimization Opportunities
- Tax-efficient investment strategies
- Contribution timing optimization
- Tax-loss harvesting opportunities

## Action Items and Next Steps
1. Review and update financial goals
2. Implement recommended investment strategy
3. Schedule regular review meetings
4. Monitor progress and adjust as needed

*This report is based on the information provided during our conversation. Please contact your financial advisor for personalized recommendations.*
    `;
  }

  public getReport(reportId: string): ReportData | null {
    return this.reports.get(reportId) || null;
  }

  public getAllReports(): ReportData[] {
    return Array.from(this.reports.values());
  }

  public deleteReport(reportId: string): boolean {
    return this.reports.delete(reportId);
  }

  public generateChartsHTML(financialData: FinancialData): string {
    try {
      console.log('🔍 Generating charts HTML for financial data:', financialData);

      const assets = financialData.assets;
      const liabilities = financialData.liabilities;
      const goals = financialData.goals;

      return `
        <div class="charts-container">
          <div class="chart-section">
            <h3>Account Balances</h3>
            <div class="chart-bar">
              <div class="bar-item">
                <span class="label">RRSP</span>
                <div class="bar">
                  <div class="bar-fill" style="width: ${Math.min((assets.rrsp / 100000) * 100, 100)}%"></div>
                </div>
                <span class="value">$${assets.rrsp.toLocaleString()}</span>
              </div>
              <div class="bar-item">
                <span class="label">TFSA</span>
                <div class="bar">
                  <div class="bar-fill" style="width: ${Math.min((assets.tfsa / 100000) * 100, 100)}%"></div>
                </div>
                <span class="value">$${assets.tfsa.toLocaleString()}</span>
              </div>
              <div class="bar-item">
                <span class="label">Investments</span>
                <div class="bar">
                  <div class="bar-fill" style="width: ${Math.min((assets.investments / 100000) * 100, 100)}%"></div>
                </div>
                <span class="value">$${assets.investments.toLocaleString()}</span>
              </div>
              <div class="bar-item">
                <span class="label">Real Estate</span>
                <div class="bar">
                  <div class="bar-fill" style="width: ${Math.min((assets.realEstate / 100000) * 100, 100)}%"></div>
                </div>
                <span class="value">$${assets.realEstate.toLocaleString()}</span>
              </div>
            </div>
          </div>

          <div class="chart-section">
            <h3>Liabilities</h3>
            <div class="chart-bar">
              <div class="bar-item">
                <span class="label">Mortgage</span>
                <div class="bar">
                  <div class="bar-fill liability" style="width: ${Math.min((liabilities.mortgage / 500000) * 100, 100)}%"></div>
                </div>
                <span class="value">$${liabilities.mortgage.toLocaleString()}</span>
              </div>
              <div class="bar-item">
                <span class="label">Credit Card</span>
                <div class="bar">
                  <div class="bar-fill liability" style="width: ${Math.min((liabilities.creditCard / 50000) * 100, 100)}%"></div>
                </div>
                <span class="value">$${liabilities.creditCard.toLocaleString()}</span>
              </div>
              <div class="bar-item">
                <span class="label">Loans</span>
                <div class="bar">
                  <div class="bar-fill liability" style="width: ${Math.min((liabilities.loans / 100000) * 100, 100)}%"></div>
                </div>
                <span class="value">$${liabilities.loans.toLocaleString()}</span>
              </div>
            </div>
          </div>

          <div class="chart-section">
            <h3>Financial Goals</h3>
            <div class="goals-grid">
              <div class="goal-item">
                <h4>Retirement</h4>
                <div class="progress-bar">
                  <div class="progress-fill" style="width: ${Math.min((goals.retirement / 1000000) * 100, 100)}%"></div>
                </div>
                <span class="goal-amount">$${goals.retirement.toLocaleString()}</span>
              </div>
              <div class="goal-item">
                <h4>Education</h4>
                <div class="progress-bar">
                  <div class="progress-fill" style="width: ${Math.min((goals.education / 100000) * 100, 100)}%"></div>
                </div>
                <span class="goal-amount">$${goals.education.toLocaleString()}</span>
              </div>
              <div class="goal-item">
                <h4>Emergency Fund</h4>
                <div class="progress-bar">
                  <div class="progress-fill" style="width: ${Math.min((goals.emergency / 50000) * 100, 100)}%"></div>
                </div>
                <span class="goal-amount">$${goals.emergency.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>

        <style>
          .charts-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            font-family: Arial, sans-serif;
          }
          
          .chart-section {
            margin-bottom: 40px;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
          }
          
          .chart-section h3 {
            margin: 0 0 20px 0;
            color: #2d3748;
            font-size: 18px;
          }
          
          .bar-item {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            gap: 15px;
          }
          
          .bar-item .label {
            min-width: 100px;
            font-weight: 500;
            color: #4a5568;
          }
          
          .bar {
            flex: 1;
            height: 20px;
            background: #e2e8f0;
            border-radius: 10px;
            overflow: hidden;
          }
          
          .bar-fill {
            height: 100%;
            background: #4299e1;
            transition: width 0.3s ease;
          }
          
          .bar-fill.liability {
            background: #f56565;
          }
          
          .bar-item .value {
            min-width: 100px;
            text-align: right;
            font-weight: 600;
            color: #2d3748;
          }
          
          .goals-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
          }
          
          .goal-item {
            text-align: center;
          }
          
          .goal-item h4 {
            margin: 0 0 10px 0;
            color: #2d3748;
            font-size: 16px;
          }
          
          .progress-bar {
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 10px;
          }
          
          .progress-fill {
            height: 100%;
            background: #48bb78;
            transition: width 0.3s ease;
          }
          
          .goal-amount {
            font-weight: 600;
            color: #2d3748;
            font-size: 14px;
          }
        </style>
      `;
    } catch (error) {
      console.error('❌ Error generating charts HTML:', error);
      return '<div class="error">Error generating charts</div>';
    }
  }
}

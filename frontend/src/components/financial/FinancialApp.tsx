'use client';

import { TooltipProvider } from '@radix-ui/react-tooltip';
import ChatMessages from '../chat/messages';
import ChatInput from '../chat/input';
import FinancialHeader from './FinancialHeader';
import useFinancialApp from '../../hooks/useFinancialApp';
import { DisplayMessage } from '../../types';

export default function FinancialApp() {
  const {
    messages,
    handleInputChange,
    handleSubmit,
    indicatorState,
    input,
    isLoading,
    setMessages,
    clearMessages,
    conversationId,
  } = useFinancialApp();

  const handleGenerateReport = async () => {
    try {
      // For now, we'll use a default client name. In a real app, you'd get this from user input or context
      const clientName = prompt("Enter client name for the financial report:");
      if (!clientName) return;

      const response = await fetch('http://localhost:8000/api/generate-report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_name: clientName,
          conversation_id: conversationId,
          report_type: 'comprehensive'
        }),
      });

      if (response.ok) {
        const result = await response.json();
        
        // Add the report URL as a message in the chat
        const reportMessage = `📊 **Financial Report Generated Successfully!**

**Client:** ${clientName}
**Report ID:** ${result.report_id}

**Report URL:** ${result.report_url}

*Copy the URL above and paste it in a new tab to view your professional financial report.*`;

        // Add the report message to the chat
        const reportChatMessage: DisplayMessage = {
          role: "assistant" as const,
          content: reportMessage,
          citations: []
        };
        
        // Update messages state
        setMessages(prevMessages => [...prevMessages, reportChatMessage]);
        
        // Also try to copy to clipboard
        try {
          await navigator.clipboard.writeText(result.report_url);
          // Add a success message to the chat
          const successMessage: DisplayMessage = {
            role: "assistant" as const,
            content: "✅ **Report URL copied to clipboard!** You can now paste it in a new tab to view your report.",
            citations: []
          };
          setMessages(prevMessages => [...prevMessages, successMessage]);
        } catch (clipboardError) {
          // Clipboard copy failed, but that's okay since the URL is in the chat
          console.log('Clipboard copy failed, but URL is displayed in chat');
          const fallbackMessage: DisplayMessage = {
            role: "assistant" as const,
            content: "📋 **Note:** Please copy the report URL above manually to view your report in a new tab.",
            citations: []
          };
          setMessages(prevMessages => [...prevMessages, fallbackMessage]);
        }
      } else {
        const errorMessage: DisplayMessage = {
          role: "assistant" as const,
          content: "❌ Failed to generate financial report. Please try again.",
          citations: []
        };
        setMessages(prevMessages => [...prevMessages, errorMessage]);
      }
    } catch (error) {
      console.error('Error generating report:', error);
      const errorMessage: DisplayMessage = {
        role: "assistant" as const,
        content: "❌ Error generating financial report. Please try again.",
        citations: []
      };
      setMessages(prevMessages => [...prevMessages, errorMessage]);
    }
  };

  return (
    <TooltipProvider>
      <div className='flex flex-col h-screen bg-gray-900'>
        <FinancialHeader clearMessages={clearMessages} onGenerateReport={handleGenerateReport} />
        
        <div className='flex-1 overflow-hidden pt-16'>
          <ChatMessages
            messages={messages}
            indicatorState={indicatorState}
          />
        </div>

        <ChatInput
          handleInputChange={handleInputChange}
          handleSubmit={handleSubmit}
          input={input}
          isLoading={isLoading}
        />
      </div>
    </TooltipProvider>
  );
}
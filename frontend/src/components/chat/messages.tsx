import React from 'react';
import { DisplayMessage, LoadingIndicator } from '../../types';

interface ChatMessagesProps {
  messages: DisplayMessage[];
  indicatorState: LoadingIndicator[];
}

const ChatMessages: React.FC<ChatMessagesProps> = ({ messages, indicatorState }) => {
  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-900 chat-scroll">
      <div className="max-w-4xl mx-auto">
        {messages.map((msg, index) => (
          <div key={index} className={`flex items-end gap-2 chat-message mb-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {/* Avatar - only show for AI messages */}
            {msg.role === 'assistant' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-sm mb-1">
                📊
              </div>
            )}
            
            {/* Message Bubble */}
            <div className={`max-w-[70%] ${msg.role === 'user' ? 'flex flex-col items-end' : 'flex flex-col items-start'}`}>
              <div className={`px-4 py-3 rounded-2xl shadow-lg relative group ${
                msg.role === 'user' 
                  ? 'bg-blue-500 text-white rounded-br-sm' 
                  : 'bg-gray-800 text-gray-100 rounded-bl-sm border border-gray-700'
              }`}>
                <div className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</div>
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-600">
                    <div className="text-xs font-medium mb-2 text-gray-400">Sources:</div>
                    {msg.citations.map((citation, idx) => (
                      <div key={idx} className="text-xs">
                        <a href={citation.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                          {citation.source_description}
                        </a>
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Copy button */}
                <button 
                  className={`absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-full ${
                    msg.role === 'user'
                      ? 'hover:bg-blue-600 text-blue-200'
                      : 'hover:bg-gray-700 text-gray-400'
                  }`}
                  onClick={() => navigator.clipboard.writeText(msg.content)}
                  title="Copy message"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </button>
              </div>
            </div>
            
            {/* Avatar - only show for user messages */}
            {msg.role === 'user' && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-sm mb-1">
                👤
              </div>
            )}
          </div>
        ))}
        
        {/* Loading indicators */}
        {indicatorState.map((indicator, index) => (
          <div key={`indicator-${index}`} className="flex items-end gap-2 mb-4 justify-start">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-sm mb-1">
              📊
            </div>
            <div className="bg-gray-800 border border-gray-700 px-4 py-3 rounded-2xl rounded-bl-sm shadow-lg">
              <div className="flex items-center gap-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
                <em className="text-sm text-gray-400">{indicator.status}</em>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ChatMessages;

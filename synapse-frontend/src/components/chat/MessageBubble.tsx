'use client';

import { Message } from '@/types';
import { User, Bot } from 'lucide-react';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex items-start space-x-3 max-w-3xl ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-blue-500' : 'bg-gray-500'
        }`}>
          {isUser ? (
            <User className="w-5 h-5 text-white" />
          ) : (
            <Bot className="w-5 h-5 text-white" />
          )}
        </div>

        {/* Message Content */}
        <div className={`flex-1 ${isUser ? 'text-right' : ''}`}>
          <div className={`inline-block px-4 py-3 rounded-2xl ${
            isUser 
              ? 'bg-blue-500 text-white' 
              : 'bg-white border border-gray-200 text-gray-900'
          }`}>
            <div className="whitespace-pre-wrap">{message.content}</div>
          </div>
          
          {/* Sources */}
          {message.sources && message.sources.length > 0 && (
            <div className="mt-3 space-y-2">
              <div className="text-xs font-medium text-gray-500">Sources:</div>
              {message.sources.map((source, index) => (
                <div key={index} className="bg-gray-50 p-3 rounded-lg border">
                  <div className="text-sm font-medium text-gray-900">{source.title}</div>
                  <div className="text-xs text-gray-600 mt-1">{source.doc}</div>
                  <div className="text-sm text-gray-700 mt-2">{source.snippet}</div>
                  {source.relevance_score && (
                    <div className="text-xs text-gray-500 mt-1">
                      Relevance: {source.relevance_score.toFixed(3)}
                      {source.confidence && ` (${source.confidence})`}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          
          {/* Timestamp */}
          <div className={`text-xs text-gray-500 mt-2 ${isUser ? 'text-right' : ''}`}>
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        </div>
      </div>
    </div>
  );
}

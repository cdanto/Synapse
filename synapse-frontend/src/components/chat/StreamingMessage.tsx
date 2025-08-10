'use client';

import { Bot } from 'lucide-react';

interface StreamingMessageProps {
  content: string;
}

export function StreamingMessage({ content }: StreamingMessageProps) {
  return (
    <div className="flex justify-start">
      <div className="flex items-start space-x-3 max-w-3xl">
        {/* Avatar */}
        <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gray-500">
          <Bot className="w-5 h-5 text-white" />
        </div>

        {/* Streaming Content */}
        <div className="flex-1">
          <div className="inline-block px-4 py-3 rounded-2xl bg-white border border-gray-200 text-gray-900">
            <div className="whitespace-pre-wrap">
              {content}
              <span className="inline-block w-2 h-4 bg-gray-400 ml-1 animate-pulse" />
            </div>
          </div>
          
          {/* Typing indicator */}
          <div className="text-xs text-gray-500 mt-2">
            Synapse is typing...
          </div>
        </div>
      </div>
    </div>
  );
}

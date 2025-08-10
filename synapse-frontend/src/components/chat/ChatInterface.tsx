'use client';

import { useEffect, useRef } from 'react';
import { useChatStore } from '@/stores/chat-store';
import { MessageBubble } from './MessageBubble';
import { StreamingMessage } from './StreamingMessage';

export function ChatInterface() {
  const { messages, isStreaming, currentStream } = useChatStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, currentStream]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b bg-white px-6 py-4">
        <h1 className="text-xl font-semibold text-gray-900">Chat with Synapse</h1>
        <p className="text-sm text-gray-600">Ask me anything or upload documents to enhance my knowledge</p>
      </div>

      {/* Messages */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-6 space-y-6"
      >
        {messages.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">🧠</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Welcome to Synapse
            </h3>
            <p className="text-gray-600 max-w-md mx-auto">
              I&apos;m your AI assistant. Start a conversation or upload documents to my knowledge base to get more accurate and contextual responses.
            </p>
          </div>
        ) : (
          messages.map((message, index) => (
            <MessageBubble key={index} message={message} />
          ))
        )}
        
        {isStreaming && <StreamingMessage content={currentStream} />}
      </div>
    </div>
  );
}

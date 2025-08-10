import { useCallback } from 'react';
import { useChatStore } from '@/stores/chat-store';
import { useConfigStore } from '@/stores/config-store';
import { Message } from '@/types';
import { apiClient, ChatMessage } from '@/lib/api';

export function useChat() {
  const { addMessage, updateLastMessage, setStreaming, appendToStream, finishStream } = useChatStore();
  const { config } = useConfigStore();

  const sendMessage = useCallback(async (content: string) => {
    // Add assistant message placeholder
    const assistantMessage: Message = {
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
    };
    addMessage(assistantMessage);

    setStreaming(true);

    try {
      // Get all messages for context
      const messages = useChatStore.getState().messages;
      const chatMessages: ChatMessage[] = messages.map(msg => ({
        role: msg.role,
        content: msg.content,
      }));

      // Add the new user message
      chatMessages.push({
        role: 'user',
        content: content,
      });

      // Prepare the request
      const request = {
        messages: chatMessages,
        temperature: config.temperature,
        top_p: config.top_p,
        max_tokens: config.max_tokens,
        auto_rag: config.auto_rag,
      };

      // Stream the response
      const stream = await apiClient.streamChat(request);
      const reader = stream.getReader();
      const decoder = new TextDecoder();

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          if (value) {
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const data = JSON.parse(line.slice(6));
                  
                  if (data.error) {
                    throw new Error(data.error);
                  }

                  if (data.delta) {
                    appendToStream(data.delta);
                  }

                  if (data.done) {
                    // Handle sources if available
                    if (data.sources && data.sources.length > 0) {
                      // Update the last message with sources
                      const lastMessage = useChatStore.getState().messages[useChatStore.getState().messages.length - 1];
                      if (lastMessage) {
                        lastMessage.sources = data.sources;
                      }
                    }
                    finishStream();
                    break;
                  }
                } catch (parseError) {
                  console.warn('Failed to parse SSE data:', parseError);
                }
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }
    } catch (error) {
      console.error('Chat error:', error);
      updateLastMessage('Sorry, there was an error processing your message.');
      setStreaming(false);
    }
  }, [addMessage, updateLastMessage, setStreaming, appendToStream, finishStream, config]);

  return { 
    sendMessage, 
    isStreaming: useChatStore.getState().isStreaming 
  };
}

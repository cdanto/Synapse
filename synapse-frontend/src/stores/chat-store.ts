import { create } from 'zustand';
import { Message } from '@/types';

interface ChatStore {
  messages: Message[];
  isStreaming: boolean;
  currentStream: string;
  
  // Actions
  addMessage: (message: Message) => void;
  updateLastMessage: (content: string) => void;
  setStreaming: (streaming: boolean) => void;
  clearChat: () => void;
  appendToStream: (content: string) => void;
  finishStream: () => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isStreaming: false,
  currentStream: '',

  addMessage: (message) => 
    set((state) => ({ 
      messages: [...state.messages, message],
      currentStream: '' // Reset stream when adding new message
    })),

  updateLastMessage: (content) =>
    set((state) => ({
      messages: state.messages.map((msg, i) => 
        i === state.messages.length - 1 ? { ...msg, content } : msg
      ),
    })),

  setStreaming: (streaming) => set({ isStreaming: streaming }),
  
  clearChat: () => set({ 
    messages: [], 
    isStreaming: false, 
    currentStream: '' 
  }),

  appendToStream: (content) =>
    set((state) => ({
      currentStream: state.currentStream + content,
    })),

  finishStream: () => {
    const { currentStream, messages } = get();
    if (currentStream && messages.length > 0) {
      // Update the last message with the complete stream content
      set((state) => ({
        messages: state.messages.map((msg, i) => 
          i === state.messages.length - 1 ? { ...msg, content: currentStream } : msg
        ),
        currentStream: '',
        isStreaming: false,
      }));
    }
  },
}));

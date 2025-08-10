# Synapse Migration Plan: Streamlit → React/TypeScript/Next.js

## Executive Summary

**Current State**: Streamlit-based frontend with FastAPI backend
**Target State**: React/TypeScript/Next.js frontend with existing FastAPI backend
**Estimated Timeline**: 3-4 weeks for a small team
**Complexity**: Medium to High (mainly due to real-time streaming and state management)

## Phase 1: Project Setup & Foundation (Week 1)

### 1.1 Next.js Project Initialization
```bash
# Create new Next.js project
npx create-next-app@latest synapse-frontend --typescript --tailwind --eslint
cd synapse-frontend

# Install dependencies
npm install @types/node @types/react @types/react-dom
npm install zustand @tanstack/react-query
npm install lucide-react clsx tailwind-merge
npm install react-hook-form @hookform/resolvers zod
```

### 1.2 Project Structure
```
synapse-frontend/
├── src/
│   ├── app/                    # Next.js 13+ app directory
│   ├── components/             # React components
│   │   ├── chat/              # Chat-related components
│   │   ├── sidebar/           # Sidebar components
│   │   ├── ui/                # Reusable UI components
│   │   └── forms/             # Form components
│   ├── hooks/                 # Custom React hooks
│   ├── lib/                   # Utilities and API client
│   ├── stores/                # Zustand state stores
│   └── types/                 # TypeScript type definitions
├── public/                    # Static assets
└── package.json
```

### 1.3 TypeScript Types Definition
```typescript
// src/types/index.ts
export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: Source[];
}

export interface Source {
  title: string;
  doc: string;
  snippet: string;
  score: number;
}

export interface Config {
  temperature: number;
  top_p: number;
  max_tokens: number;
  auto_rag: boolean;
  rag_top_k: number;
  rag_max_chars: number;
}

export interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  currentStream: string;
}
```

## Phase 2: API Client & State Management (Week 1-2)

### 2.1 API Client Migration
```typescript
// src/lib/api-client.ts
export class APIClient {
  private baseURL: string;
  private authToken?: string;

  constructor(baseURL: string = 'http://127.0.0.1:9000') {
    this.baseURL = baseURL;
  }

  async chatStream(
    messages: Message[],
    options: {
      temperature?: number;
      max_tokens?: number;
      auto_rag?: boolean;
    }
  ): Promise<ReadableStream<Uint8Array>> {
    const response = await fetch(`${this.baseURL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        ...(this.authToken && { Authorization: `Bearer ${this.authToken}` }),
      },
      body: JSON.stringify({
        messages,
        ...options,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.body!;
  }

  // Other methods: getConfig, setConfig, kbUpload, etc.
}
```

### 2.2 State Management with Zustand
```typescript
// src/stores/chat-store.ts
import { create } from 'zustand';
import { Message, Source } from '@/types';

interface ChatStore {
  messages: Message[];
  isStreaming: boolean;
  currentStream: string;
  
  addMessage: (message: Message) => void;
  updateLastMessage: (content: string) => void;
  setStreaming: (streaming: boolean) => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [],
  isStreaming: false,
  currentStream: '',

  addMessage: (message) => 
    set((state) => ({ messages: [...state.messages, message] })),

  updateLastMessage: (content) =>
    set((state) => ({
      messages: state.messages.map((msg, i) => 
        i === state.messages.length - 1 ? { ...msg, content } : msg
      ),
    })),

  setStreaming: (streaming) => set({ isStreaming: streaming }),
  clearChat: () => set({ messages: [] }),
}));
```

## Phase 3: Core Components Migration (Week 2-3)

### 3.1 Chat Interface Component
```typescript
// src/components/chat/ChatInterface.tsx
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
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 space-y-4"
      >
        {messages.map((message, index) => (
          <MessageBubble key={index} message={message} />
        ))}
        {isStreaming && <StreamingMessage content={currentStream} />}
      </div>
    </div>
  );
}
```

### 3.2 Sidebar Component
```typescript
// src/components/sidebar/Sidebar.tsx
'use client';

import { useState } from 'react';
import { useConfigStore } from '@/stores/config-store';
import { RAGControls } from './RAGControls';
import { KnowledgeBase } from './KnowledgeBase';
import { ChatControls } from './ChatControls';

export function Sidebar() {
  const [activeTab, setActiveTab] = useState<'chat' | 'rag' | 'kb'>('chat');

  return (
    <aside className="w-80 bg-gray-50 border-r border-gray-200 p-4">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">🧠 Synapse</h2>
        <p className="text-gray-600">Your AI Assistant</p>
      </div>

      <nav className="mb-6">
        <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
          {[
            { id: 'chat', label: 'Chat', icon: '💬' },
            { id: 'rag', label: 'RAG', icon: '🔍' },
            { id: 'kb', label: 'KB', icon: '📚' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>
      </nav>

      {activeTab === 'chat' && <ChatControls />}
      {activeTab === 'rag' && <RAGControls />}
      {activeTab === 'kb' && <KnowledgeBase />}
    </aside>
  );
}
```

### 3.3 Message Composition Component
```typescript
// src/components/chat/MessageComposer.tsx
'use client';

import { useState, useRef } from 'react';
import { useForm } from 'react-hook-form';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/Textarea';
import { useChatStore } from '@/stores/chat-store';
import { useChat } from '@/hooks/use-chat';

interface ComposeForm {
  message: string;
}

export function MessageComposer() {
  const { register, handleSubmit, reset, watch } = useForm<ComposeForm>();
  const { addMessage } = useChatStore();
  const { sendMessage, isStreaming } = useChat();
  const message = watch('message');

  const onSubmit = async (data: ComposeForm) => {
    if (!data.message.trim() || isStreaming) return;

    const userMessage = {
      role: 'user' as const,
      content: data.message.trim(),
      timestamp: new Date().toISOString(),
    };

    addMessage(userMessage);
    reset();
    
    await sendMessage(data.message.trim());
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="border-t bg-white p-4">
      <div className="flex space-x-2">
        <Textarea
          {...register('message')}
          placeholder="Type your message... Shift+Enter for newline"
          className="flex-1 resize-none"
          rows={3}
          disabled={isStreaming}
        />
        <Button 
          type="submit" 
          disabled={!message?.trim() || isStreaming}
          className="self-end"
        >
          {isStreaming ? 'Sending...' : 'Send'}
        </Button>
      </div>
    </form>
  );
}
```

## Phase 4: Real-time Streaming Implementation (Week 3)

### 4.1 Streaming Hook
```typescript
// src/hooks/use-chat.ts
import { useCallback } from 'react';
import { useChatStore } from '@/stores/chat-store';
import { useConfigStore } from '@/stores/config-store';
import { APIClient } from '@/lib/api-client';
import { Message } from '@/types';

export function useChat() {
  const { addMessage, updateLastMessage, setStreaming } = useChatStore();
  const { config } = useConfigStore();
  const apiClient = new APIClient();

  const sendMessage = useCallback(async (content: string) => {
    const messages = useChatStore.getState().messages;
    
    // Add assistant message placeholder
    const assistantMessage: Message = {
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
    };
    addMessage(assistantMessage);

    setStreaming(true);

    try {
      const stream = await apiClient.chatStream(messages, {
        temperature: config.temperature,
        max_tokens: config.max_tokens,
        auto_rag: config.auto_rag,
      });

      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              setStreaming(false);
              return;
            }

            try {
              const parsed = JSON.parse(data);
              if (parsed.delta) {
                fullContent += parsed.delta;
                updateLastMessage(fullContent);
              }
            } catch (e) {
              // Skip invalid JSON
            }
          }
        }
      }
    } catch (error) {
      console.error('Streaming error:', error);
      updateLastMessage('Sorry, there was an error processing your message.');
    } finally {
      setStreaming(false);
    }
  }, [config, addMessage, updateLastMessage, setStreaming]);

  return { sendMessage, isStreaming: useChatStore.getState().isStreaming };
}
```

### 4.2 SSE Event Handling
```typescript
// src/lib/sse-handler.ts
export class SSEHandler {
  private eventSource: EventSource | null = null;

  connect(url: string, handlers: {
    onMessage?: (data: any) => void;
    onError?: (error: Event) => void;
    onOpen?: () => void;
  }) {
    this.eventSource = new EventSource(url);

    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handlers.onMessage?.(data);
      } catch (e) {
        console.error('Failed to parse SSE data:', e);
      }
    };

    this.eventSource.onerror = handlers.onError;
    this.eventSource.onopen = handlers.onOpen;

    return this.eventSource;
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
```

## Phase 5: Advanced Features & Polish (Week 4)

### 5.1 File Upload Component
```typescript
// src/components/kb/FileUpload.tsx
'use client';

import { useState, useRef } from 'react';
import { Upload, X, FileText } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useKnowledgeBase } from '@/hooks/use-knowledge-base';

export function FileUpload() {
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { uploadFiles, reloadKB } = useKnowledgeBase();

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || []);
    setFiles(prev => [...prev, ...selectedFiles]);
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setIsUploading(true);
    try {
      await uploadFiles(files);
      await reloadKB();
      setFiles([]);
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
        <Upload className="mx-auto h-12 w-12 text-gray-400" />
        <div className="mt-4">
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading}
          >
            Select Files
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".txt,.md,.pdf,.docx,.csv,.json"
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium">Selected Files:</h4>
          {files.map((file, index) => (
            <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
              <div className="flex items-center space-x-2">
                <FileText className="h-4 w-4 text-gray-500" />
                <span className="text-sm">{file.name}</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeFile(index)}
                disabled={isUploading}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
          
          <Button
            onClick={handleUpload}
            disabled={isUploading || files.length === 0}
            className="w-full"
          >
            {isUploading ? 'Uploading...' : `Upload ${files.length} File(s)`}
          </Button>
        </div>
      )}
    </div>
  );
}
```

### 5.2 Configuration Management
```typescript
// src/components/config/ConfigPanel.tsx
'use client';

import { useForm } from 'react-hook-form';
import { useConfigStore } from '@/stores/config-store';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Switch } from '@/components/ui/Switch';

export function ConfigPanel() {
  const { config, updateConfig } = useConfigStore();
  const { register, handleSubmit, formState: { isDirty } } = useForm({
    defaultValues: config,
  });

  const onSubmit = async (data: any) => {
    await updateConfig(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <label className="text-sm font-medium">Temperature</label>
        <Input
          type="number"
          step="0.1"
          min="0"
          max="2"
          {...register('temperature', { valueAsNumber: true })}
        />
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Max Tokens</label>
        <Input
          type="number"
          min="1"
          max="4000"
          {...register('max_tokens', { valueAsNumber: true })}
        />
      </div>

      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">Auto RAG</label>
        <Switch
          {...register('auto_rag')}
          checked={config.auto_rag}
          onCheckedChange={(checked) => updateConfig({ auto_rag: checked })}
        />
      </div>

      <Button type="submit" disabled={!isDirty} className="w-full">
        Save Changes
      </Button>
    </form>
  );
}
```

## Phase 6: Testing & Deployment (Week 4)

### 6.1 Testing Strategy
- **Unit Tests**: Jest + React Testing Library for components
- **Integration Tests**: API client and state management
- **E2E Tests**: Playwright for critical user flows
- **Performance Tests**: Lighthouse CI for performance metrics

### 6.2 Build & Deployment
```bash
# Build for production
npm run build

# Start production server
npm start

# Docker deployment
docker build -t synapse-frontend .
docker run -p 3000:3000 synapse-frontend
```

## Migration Checklist

### ✅ Phase 1: Foundation
- [ ] Next.js project setup
- [ ] TypeScript configuration
- [ ] Tailwind CSS setup
- [ ] Project structure creation

### ✅ Phase 2: Core Infrastructure
- [ ] API client migration
- [ ] State management setup
- [ ] Type definitions
- [ ] Utility functions

### ✅ Phase 3: Component Migration
- [ ] Chat interface
- [ ] Sidebar component
- [ ] Message composer
- [ ] Basic UI components

### ✅ Phase 4: Advanced Features
- [ ] Real-time streaming
- [ ] SSE handling
- [ ] File uploads
- [ ] Configuration management

### ✅ Phase 5: Polish & Testing
- [ ] Error handling
- [ ] Loading states
- [ ] Responsive design
- [ ] Accessibility improvements

### ✅ Phase 6: Deployment
- [ ] Production build
- [ ] Performance optimization
- [ ] Monitoring setup
- [ ] Documentation updates

## Risk Mitigation

### High-Risk Areas
1. **Streaming Implementation**: Start with simple polling, then upgrade to SSE
2. **State Synchronization**: Use React Query for server state, Zustand for UI state
3. **File Uploads**: Implement progressive enhancement with fallbacks

### Fallback Strategies
- Keep Streamlit version running in parallel during migration
- Implement feature flags for gradual rollout
- Maintain API compatibility for easy rollback

## Success Metrics

- **Performance**: 50%+ improvement in page load times
- **User Experience**: Better responsiveness and animations
- **Developer Experience**: Faster development cycles
- **Maintainability**: Cleaner code structure and better tooling

## Next Steps

1. **Immediate**: Set up Next.js project and basic structure
2. **Week 1**: Implement core components and state management
3. **Week 2**: Add streaming and real-time features
4. **Week 3**: Polish UI and add advanced features
5. **Week 4**: Testing, optimization, and deployment

This migration will significantly improve your application's performance, maintainability, and user experience while leveraging your existing robust FastAPI backend.

## Phase 7: Performance Optimization & Advanced Features (Week 4-5)

### 7.1 Code Splitting & Lazy Loading
```typescript
// src/app/layout.tsx
import dynamic from 'next/dynamic';

// Lazy load heavy components
const Sidebar = dynamic(() => import('@/components/sidebar/Sidebar'), {
  loading: () => <div className="w-80 bg-gray-50 animate-pulse" />,
  ssr: false
});

const ChatInterface = dynamic(() => import('@/components/chat/ChatInterface'), {
  loading: () => <div className="flex-1 bg-white animate-pulse" />,
  ssr: false
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="flex h-screen">
          <Sidebar />
          <main className="flex-1 flex flex-col">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
```

### 7.2 Virtual Scrolling for Large Chat Histories
```typescript
// src/components/chat/VirtualizedChat.tsx
'use client';

import { useVirtualizer } from '@tanstack/react-virtual';
import { useRef, useEffect } from 'react';
import { useChatStore } from '@/stores/chat-store';
import { MessageBubble } from './MessageBubble';

export function VirtualizedChat() {
  const { messages } = useChatStore();
  const parentRef = useRef<HTMLDivElement>(null);

  const rowVirtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 100, // Estimated message height
    overscan: 5,
  });

  useEffect(() => {
    // Scroll to bottom when new messages arrive
    if (messages.length > 0) {
      rowVirtualizer.scrollToIndex(messages.length - 1);
    }
  }, [messages.length, rowVirtualizer]);

  return (
    <div
      ref={parentRef}
      className="h-full overflow-auto"
      style={{
        contain: 'strict',
      }}
    >
      <div
        style={{
          height: `${rowVirtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {rowVirtualizer.getVirtualItems().map((virtualRow) => {
          const message = messages[virtualRow.index];
          return (
            <div
              key={virtualRow.index}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              <MessageBubble message={message} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

### 7.3 Advanced RAG Controls with Real-time Feedback
```typescript
// src/components/rag/AdvancedRAGControls.tsx
'use client';

import { useState, useEffect } from 'react';
import { useRAGStore } from '@/stores/rag-store';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Switch } from '@/components/ui/Switch';
import { Progress } from '@/components/ui/Progress';
import { 
  Search, 
  Settings, 
  Database, 
  TrendingUp,
  Clock,
  FileText 
} from 'lucide-react';

export function AdvancedRAGControls() {
  const { 
    config, 
    updateConfig, 
    searchQuery, 
    setSearchQuery,
    searchResults,
    isSearching,
    searchStats 
  } = useRAGStore();

  const [localConfig, setLocalConfig] = useState(config);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleConfigChange = (key: string, value: any) => {
    const newConfig = { ...localConfig, [key]: value };
    setLocalConfig(newConfig);
    updateConfig(newConfig);
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    // Trigger RAG search
  };

  return (
    <div className="space-y-6">
      {/* Search Section */}
      <div className="space-y-3">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Search className="h-5 w-5" />
          RAG Search
        </h3>
        
        <div className="flex gap-2">
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search knowledge base..."
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <Button 
            onClick={handleSearch}
            disabled={isSearching || !searchQuery.trim()}
          >
            {isSearching ? 'Searching...' : 'Search'}
          </Button>
        </div>

        {isSearching && (
          <div className="space-y-2">
            <Progress value={searchStats.progress} className="w-full" />
            <p className="text-sm text-gray-600">
              Searching {searchStats.documentsProcessed} documents...
            </p>
          </div>
        )}
      </div>

      {/* Configuration Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Settings className="h-5 w-5" />
            RAG Configuration
          </h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            {showAdvanced ? 'Hide' : 'Advanced'}
          </Button>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-sm font-medium">Top K Results</label>
              <Input
                type="number"
                min="1"
                max="20"
                value={localConfig.top_k}
                onChange={(e) => handleConfigChange('top_k', parseInt(e.target.value))}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Max Chars</label>
              <Input
                type="number"
                min="100"
                max="10000"
                value={localConfig.max_chars}
                onChange={(e) => handleConfigChange('max_chars', parseInt(e.target.value))}
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <label className="text-sm font-medium">Auto RAG</label>
            <Switch
              checked={localConfig.auto_rag}
              onCheckedChange={(checked) => handleConfigChange('auto_rag', checked)}
            />
          </div>

          {showAdvanced && (
            <div className="space-y-3 pt-3 border-t">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-medium">Similarity Threshold</label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    value={localConfig.similarity_threshold}
                    onChange={(e) => handleConfigChange('similarity_threshold', parseFloat(e.target.value))}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Chunk Size</label>
                  <Input
                    type="number"
                    min="100"
                    max="2000"
                    value={localConfig.chunk_size}
                    onChange={(e) => handleConfigChange('chunk_size', parseInt(e.target.value))}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Statistics Section */}
      {searchStats && (
        <div className="space-y-3 pt-3 border-t">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Search Statistics
          </h3>
          
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-blue-500" />
              <span>{searchStats.documentsProcessed} docs</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-green-500" />
              <span>{searchStats.searchTime}ms</span>
            </div>
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-purple-500" />
              <span>{searchStats.chunksRetrieved} chunks</span>
            </div>
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-orange-500" />
              <span>{searchStats.averageScore.toFixed(2)} score</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

### 7.4 Enhanced Message Components with Rich Content
```typescript
// src/components/chat/EnhancedMessageBubble.tsx
'use client';

import { useState } from 'react';
import { Message, Source } from '@/types';
import { 
  Copy, 
  Check, 
  ExternalLink, 
  ChevronDown, 
  ChevronUp,
  FileText,
  Quote
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

interface EnhancedMessageBubbleProps {
  message: Message;
  onCopy?: (content: string) => void;
}

export function EnhancedMessageBubble({ message, onCopy }: EnhancedMessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const isUser = message.role === 'user';
  const hasSources = message.sources && message.sources.length > 0;

  const handleCopy = async () => {
    if (onCopy) {
      onCopy(message.content);
    } else {
      await navigator.clipboard.writeText(message.content);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toggleExpanded = () => setExpanded(!expanded);

  return (
    <div className={cn(
      "group relative rounded-lg p-4 transition-all",
      isUser 
        ? "bg-blue-50 border border-blue-200 ml-12" 
        : "bg-white border border-gray-200 mr-12"
    )}>
      {/* Message Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={cn(
            "text-sm font-medium",
            isUser ? "text-blue-700" : "text-gray-700"
          )}>
            {isUser ? 'You' : 'Synapse'}
          </span>
          <span className="text-xs text-gray-500">
            {new Date(message.timestamp).toLocaleTimeString()}
          </span>
        </div>
        
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-8 w-8 p-0"
          >
            {copied ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
          </Button>
          
          {!isUser && (
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleExpanded}
              className="h-8 w-8 p-0"
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          )}
        </div>
      </div>

      {/* Message Content */}
      <div className="prose prose-sm max-w-none">
        <div className={cn(
          "whitespace-pre-wrap",
          !expanded && !isUser && message.content.length > 500 && "line-clamp-6"
        )}>
          {message.content}
        </div>
        
        {!expanded && !isUser && message.content.length > 500 && (
          <button
            onClick={toggleExpanded}
            className="text-blue-600 hover:text-blue-800 text-sm font-medium mt-2"
          >
            Show more...
          </button>
        )}
      </div>

      {/* Sources Section */}
      {hasSources && (
        <div className="mt-4 pt-3 border-t border-gray-100">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-gray-700 flex items-center gap-2">
              <Quote className="h-4 w-4" />
              Sources ({message.sources!.length})
            </h4>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowSources(!showSources)}
              className="h-7 px-2 text-xs"
            >
              {showSources ? 'Hide' : 'Show'} Sources
            </Button>
          </div>

          {showSources && (
            <div className="space-y-2">
              {message.sources!.map((source, index) => (
                <div key={index} className="bg-gray-50 rounded p-3 text-sm">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <h5 className="font-medium text-gray-900 truncate">
                        {source.title}
                      </h5>
                      <p className="text-gray-600 text-xs mt-1">
                        Score: {source.score.toFixed(3)}
                      </p>
                      <p className="text-gray-700 mt-2 text-xs leading-relaxed">
                        {source.snippet}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 w-7 p-0 flex-shrink-0"
                      onClick={() => window.open(source.doc, '_blank')}
                    >
                      <ExternalLink className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

## Phase 8: Security & Authentication (Week 5)

### 8.1 Authentication Context & Hooks
```typescript
// src/contexts/auth-context.tsx
'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { User, Session } from '@/types';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      if (token) {
        const response = await fetch('/api/auth/me', {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
          setSession({ token, expiresAt: Date.now() + 24 * 60 * 60 * 1000 });
        } else {
          localStorage.removeItem('auth_token');
        }
      }
    } catch (error) {
      console.error('Auth check failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const signIn = async (email: string, password: string) => {
    const response = await fetch('/api/auth/signin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (!response.ok) {
      throw new Error('Authentication failed');
    }

    const { token, user: userData } = await response.json();
    localStorage.setItem('auth_token', token);
    setUser(userData);
    setSession({ token, expiresAt: Date.now() + 24 * 60 * 60 * 1000 });
  };

  const signOut = async () => {
    localStorage.removeItem('auth_token');
    setUser(null);
    setSession(null);
  };

  const refreshSession = async () => {
    // Implement token refresh logic
  };

  return (
    <AuthContext.Provider value={{
      user,
      session,
      isLoading,
      signIn,
      signOut,
      refreshSession
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
```

### 8.2 Protected Routes & Middleware
```typescript
// src/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth_token')?.value;
  const isAuthPage = request.nextUrl.pathname.startsWith('/auth');
  const isProtectedRoute = request.nextUrl.pathname.startsWith('/dashboard') ||
                          request.nextUrl.pathname.startsWith('/admin');

  // Redirect to login if accessing protected route without token
  if (isProtectedRoute && !token) {
    return NextResponse.redirect(new URL('/auth/login', request.url));
  }

  // Redirect to dashboard if accessing auth page with valid token
  if (isAuthPage && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/admin/:path*',
    '/auth/:path*',
  ],
};
```

### 8.3 API Rate Limiting & Security
```typescript
// src/lib/rate-limiter.ts
export class RateLimiter {
  private requests: Map<string, number[]> = new Map();
  private readonly maxRequests: number;
  private readonly windowMs: number;

  constructor(maxRequests: number = 100, windowMs: number = 60000) {
    this.maxRequests = maxRequests;
    this.windowMs = windowMs;
  }

  isAllowed(identifier: string): boolean {
    const now = Date.now();
    const windowStart = now - this.windowMs;
    
    if (!this.requests.has(identifier)) {
      this.requests.set(identifier, [now]);
      return true;
    }

    const requests = this.requests.get(identifier)!;
    const validRequests = requests.filter(time => time > windowStart);
    
    if (validRequests.length >= this.maxRequests) {
      return false;
    }

    validRequests.push(now);
    this.requests.set(identifier, validRequests);
    return true;
  }

  getRemaining(identifier: string): number {
    const now = Date.now();
    const windowStart = now - this.windowMs;
    
    if (!this.requests.has(identifier)) {
      return this.maxRequests;
    }

    const requests = this.requests.get(identifier)!;
    const validRequests = requests.filter(time => time > windowStart);
    
    return Math.max(0, this.maxRequests - validRequests.length);
  }

  reset(identifier: string): void {
    this.requests.delete(identifier);
  }
}

// Usage in API routes
export function withRateLimit(
  handler: Function,
  maxRequests: number = 100,
  windowMs: number = 60000
) {
  const limiter = new RateLimiter(maxRequests, windowMs);
  
  return async (req: Request, context: any) => {
    const identifier = req.headers.get('x-forwarded-for') || 'unknown';
    
    if (!limiter.isAllowed(identifier)) {
      return new Response('Rate limit exceeded', { status: 429 });
    }
    
    return handler(req, context);
  };
}
```

## Phase 9: Monitoring & Analytics (Week 5-6)

### 9.1 Performance Monitoring
```typescript
// src/lib/performance-monitor.ts
export class PerformanceMonitor {
  private metrics: Map<string, number[]> = new Map();
  private observers: PerformanceObserver[] = [];

  constructor() {
    this.setupObservers();
  }

  private setupObservers() {
    // Core Web Vitals
    if ('PerformanceObserver' in window) {
      // LCP (Largest Contentful Paint)
      const lcpObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const lastEntry = entries[entries.length - 1];
        this.recordMetric('lcp', lastEntry.startTime);
      });
      lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });

      // FID (First Input Delay)
      const fidObserver = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach((entry) => {
          this.recordMetric('fid', entry.processingStart - entry.startTime);
        });
      });
      fidObserver.observe({ entryTypes: ['first-input'] });

      // CLS (Cumulative Layout Shift)
      const clsObserver = new PerformanceObserver((list) => {
        let clsValue = 0;
        const entries = list.getEntries();
        entries.forEach((entry: any) => {
          if (!entry.hadRecentInput) {
            clsValue += entry.value;
          }
        });
        this.recordMetric('cls', clsValue);
      });
      clsObserver.observe({ entryTypes: ['layout-shift'] });

      this.observers.push(lcpObserver, fidObserver, clsObserver);
    }
  }

  recordMetric(name: string, value: number) {
    if (!this.metrics.has(name)) {
      this.metrics.set(name, []);
    }
    this.metrics.get(name)!.push(value);
    
    // Send to analytics if threshold exceeded
    this.checkThresholds(name, value);
  }

  private checkThresholds(name: string, value: number) {
    const thresholds: Record<string, { good: number; poor: number }> = {
      lcp: { good: 2500, poor: 4000 },
      fid: { good: 100, poor: 300 },
      cls: { good: 0.1, poor: 0.25 }
    };

    const threshold = thresholds[name];
    if (threshold) {
      let rating = 'good';
      if (value > threshold.poor) rating = 'poor';
      else if (value > threshold.good) rating = 'needs-improvement';

      this.sendAnalytics(name, value, rating);
    }
  }

  private sendAnalytics(metric: string, value: number, rating: string) {
    // Send to your analytics service
    if (typeof gtag !== 'undefined') {
      gtag('event', 'web_vitals', {
        event_category: 'Web Vitals',
        event_label: metric,
        value: Math.round(value),
        custom_parameter_rating: rating
      });
    }
  }

  getMetrics() {
    const result: Record<string, { current: number; average: number; count: number }> = {};
    
    for (const [name, values] of this.metrics) {
      result[name] = {
        current: values[values.length - 1] || 0,
        average: values.reduce((a, b) => a + b, 0) / values.length,
        count: values.length
      };
    }
    
    return result;
  }

  destroy() {
    this.observers.forEach(observer => observer.disconnect());
  }
}

// Usage in app
export function usePerformanceMonitoring() {
  useEffect(() => {
    const monitor = new PerformanceMonitor();
    
    return () => monitor.destroy();
  }, []);
}
```

### 9.2 Error Boundary & Error Tracking
```typescript
// src/components/error-boundary.tsx
'use client';

import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ComponentType<{ error: Error; resetError: () => void }>;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ error, errorInfo });
    
    // Log error to your error tracking service
    console.error('Error caught by boundary:', error, errorInfo);
    
    // Send to analytics/error tracking
    if (typeof gtag !== 'undefined') {
      gtag('event', 'exception', {
        description: error.message,
        fatal: false
      });
    }
  }

  resetError = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return <this.props.fallback error={this.state.error!} resetError={this.resetError} />;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
            <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
              <AlertTriangle className="h-6 w-6 text-red-600" />
            </div>
            
            <h1 className="text-lg font-semibold text-gray-900 mb-2">
              Something went wrong
            </h1>
            
            <p className="text-gray-600 mb-6">
              We encountered an unexpected error. Please try refreshing the page or contact support if the problem persists.
            </p>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="text-left mb-6 p-4 bg-gray-50 rounded text-sm">
                <summary className="cursor-pointer font-medium mb-2">
                  Error Details (Development)
                </summary>
                <pre className="text-red-600 overflow-auto">
                  {this.state.error.stack}
                </pre>
              </details>
            )}

            <div className="flex flex-col gap-3">
              <Button onClick={this.resetError} className="w-full">
                <RefreshCw className="h-4 w-4 mr-2" />
                Try Again
              </Button>
              
              <Button variant="outline" onClick={() => window.location.href = '/'} className="w-full">
                <Home className="h-4 w-4 mr-2" />
                Go Home
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Usage
export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  fallback?: React.ComponentType<{ error: Error; resetError: () => void }>
) {
  return function WrappedComponent(props: P) {
    return (
      <ErrorBoundary fallback={fallback}>
        <Component {...props} />
      </ErrorBoundary>
    );
  };
}
```

## Phase 10: Post-Migration Support & Optimization (Week 6+)

### 10.1 A/B Testing Framework
```typescript
// src/lib/ab-testing.ts
interface Experiment {
  id: string;
  name: string;
  variants: string[];
  weights: number[];
  startDate: Date;
  endDate?: Date;
}

export class ABTesting {
  private experiments: Map<string, Experiment> = new Map();
  private assignments: Map<string, string> = new Map();

  constructor() {
    this.loadExperiments();
  }

  private loadExperiments() {
    // Load experiments from config or API
    const experiments: Experiment[] = [
      {
        id: 'chat_interface_v2',
        name: 'Chat Interface Version 2',
        variants: ['control', 'treatment'],
        weights: [0.5, 0.5],
        startDate: new Date('2024-01-01'),
      },
      {
        id: 'sidebar_layout',
        name: 'Sidebar Layout Optimization',
        variants: ['compact', 'expanded', 'collapsible'],
        weights: [0.33, 0.33, 0.34],
        startDate: new Date('2024-01-01'),
      }
    ];

    experiments.forEach(exp => this.experiments.set(exp.id, exp));
  }

  getVariant(experimentId: string, userId: string): string {
    const key = `${experimentId}:${userId}`;
    
    if (this.assignments.has(key)) {
      return this.assignments.get(key)!;
    }

    const experiment = this.experiments.get(experimentId);
    if (!experiment || this.isExperimentExpired(experiment)) {
      return 'control';
    }

    const variant = this.selectVariant(experiment);
    this.assignments.set(key, variant);
    
    // Track assignment
    this.trackAssignment(experimentId, variant, userId);
    
    return variant;
  }

  private selectVariant(experiment: Experiment): string {
    const random = Math.random();
    let cumulativeWeight = 0;
    
    for (let i = 0; i < experiment.variants.length; i++) {
      cumulativeWeight += experiment.weights[i];
      if (random <= cumulativeWeight) {
        return experiment.variants[i];
      }
    }
    
    return experiment.variants[0];
  }

  private isExperimentExpired(experiment: Experiment): boolean {
    const now = new Date();
    return now < experiment.startDate || 
           (experiment.endDate && now > experiment.endDate);
  }

  private trackAssignment(experimentId: string, variant: string, userId: string) {
    if (typeof gtag !== 'undefined') {
      gtag('event', 'experiment_impression', {
        experiment_id: experimentId,
        variant: variant,
        user_id: userId
      });
    }
  }

  trackConversion(experimentId: string, variant: string, userId: string, value?: number) {
    if (typeof gtag !== 'undefined') {
      gtag('event', 'experiment_conversion', {
        experiment_id: experimentId,
        variant: variant,
        user_id: userId,
        value: value
      });
    }
  }
}

// Usage in components
export function useABTest(experimentId: string, userId: string) {
  const [variant, setVariant] = useState<string>('control');
  
  useEffect(() => {
    const abTesting = new ABTesting();
    const variant = abTesting.getVariant(experimentId, userId);
    setVariant(variant);
  }, [experimentId, userId]);

  return variant;
}
```

### 10.2 Progressive Web App Features
```typescript
// src/lib/pwa-manager.ts
export class PWAManager {
  private deferredPrompt: any;
  private isInstalled: boolean = false;

  constructor() {
    this.setupEventListeners();
    this.checkInstallationStatus();
  }

  private setupEventListeners() {
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      this.deferredPrompt = e;
      this.showInstallPrompt();
    });

    window.addEventListener('appinstalled', () => {
      this.isInstalled = true;
      this.hideInstallPrompt();
      this.trackInstallation();
    });
  }

  private checkInstallationStatus() {
    // Check if app is installed
    if (window.matchMedia('(display-mode: standalone)').matches ||
        (window.navigator as any).standalone === true) {
      this.isInstalled = true;
    }
  }

  private showInstallPrompt() {
    // Show custom install button
    const installButton = document.getElementById('pwa-install');
    if (installButton) {
      installButton.style.display = 'block';
      installButton.addEventListener('click', () => this.installApp());
    }
  }

  private hideInstallPrompt() {
    const installButton = document.getElementById('pwa-install');
    if (installButton) {
      installButton.style.display = 'none';
    }
  }

  private async installApp() {
    if (!this.deferredPrompt) return;

    this.deferredPrompt.prompt();
    const { outcome } = await this.deferredPrompt.userChoice;
    
    if (outcome === 'accepted') {
      console.log('User accepted the install prompt');
    } else {
      console.log('User dismissed the install prompt');
    }
    
    this.deferredPrompt = null;
  }

  private trackInstallation() {
    if (typeof gtag !== 'undefined') {
      gtag('event', 'pwa_install', {
        event_category: 'PWA',
        event_label: 'App Installation'
      });
    }
  }

  // Service Worker Registration
  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js');
        console.log('SW registered: ', registration);
        
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                this.showUpdatePrompt();
              }
            });
          }
        });
      } catch (error) {
        console.log('SW registration failed: ', error);
      }
    }
  }

  private showUpdatePrompt() {
    // Show update available prompt
    const updateButton = document.getElementById('pwa-update');
    if (updateButton) {
      updateButton.style.display = 'block';
      updateButton.addEventListener('click', () => window.location.reload());
    }
  }
}

// Service Worker (public/sw.js)
const CACHE_NAME = 'synapse-v1';
const urlsToCache = [
  '/',
  '/static/js/bundle.js',
  '/static/css/main.css',
  '/manifest.json'
];

self.addEventListener('install', (event: any) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', (event: any) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => response || fetch(event.request))
  );
});
```

## Final Implementation Checklist

### ✅ Core Features
- [ ] Next.js 13+ App Router setup
- [ ] TypeScript configuration
- [ ] Tailwind CSS styling
- [ ] Component architecture
- [ ] State management with Zustand
- [ ] API client implementation

### ✅ Chat Functionality
- [ ] Real-time streaming
- [ ] Message composition
- [ ] Chat history
- [ ] RAG integration
- [ ] Source citations

### ✅ Advanced Features
- [ ] File uploads
- [ ] Configuration management
- [ ] Virtual scrolling
- [ ] Error boundaries
- [ ] Performance monitoring

### ✅ Security & Performance
- [ ] Authentication system
- [ ] Rate limiting
- [ ] PWA features
- [ ] Code splitting
- [ ] Performance optimization

### ✅ Testing & Deployment
- [ ] Unit tests
- [ ] Integration tests
- [ ] E2E tests
- [ ] Production build
- [ ] Monitoring setup

## Post-Migration Support

### Week 6-8: Optimization & Monitoring
- Performance tuning based on real user data
- A/B testing of UI improvements
- User feedback collection and iteration
- Bug fixes and stability improvements

### Month 2-3: Feature Enhancement
- Advanced RAG capabilities
- Multi-modal support (images, documents)
- Collaboration features
- Mobile app development

### Ongoing: Maintenance & Growth
- Regular dependency updates
- Security patches
- Performance monitoring
- User experience improvements

This comprehensive migration plan provides a solid foundation for transforming your Streamlit application into a modern, scalable React/TypeScript frontend while maintaining all existing functionality and adding new capabilities for future growth.

# Quick Start: Begin Your Migration Today

## 🚀 Immediate Actions (Next 30 minutes)

### 1. Create Your Next.js Project
```bash
# Navigate to your Synapse directory
cd /Users/cdanto/Documents/Synapse

# Create the new frontend project
npx create-next-app@latest synapse-frontend --typescript --tailwind --eslint --yes

# Navigate into the new project
cd synapse-frontend

# Install essential dependencies
npm install zustand @tanstack/react-query lucide-react clsx tailwind-merge
npm install react-hook-form @hookform/resolvers zod
```

### 2. Set Up Project Structure
```bash
# Create the directory structure
mkdir -p src/{components/{chat,sidebar,ui,forms},hooks,lib,stores,types}
mkdir -p src/components/{chat,sidebar,ui,forms}
```

### 3. Configure TypeScript Paths
```json
// tsconfig.json - Add this to compilerOptions
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### 4. Create Your First Component
```typescript
// src/components/chat/MessageBubble.tsx
'use client';

import { Message } from '@/types';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[80%] rounded-lg px-4 py-2 ${
        isUser 
          ? 'bg-blue-500 text-white' 
          : 'bg-gray-100 text-gray-900'
      }`}>
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.sources && message.sources.length > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-200">
            <p className="text-xs text-gray-500">Sources:</p>
            {message.sources.map((source, index) => (
              <div key={index} className="text-xs">
                {source.title} - {source.doc}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

### 5. Create Basic Types
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
```

### 6. Test Your Setup
```bash
# Start the development server
npm run dev

# Open http://localhost:3000 in your browser
# You should see the Next.js welcome page
```

## 🔧 Next Steps (Next 2 hours)

### 1. Create Basic Layout
```typescript
// src/app/layout.tsx
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Synapse - Your AI Assistant',
  description: 'AI-powered chat with RAG capabilities',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          {children}
        </div>
      </body>
    </html>
  )
}
```

### 2. Create Main Page
```typescript
// src/app/page.tsx
import { ChatInterface } from '@/components/chat/ChatInterface'
import { Sidebar } from '@/components/sidebar/Sidebar'

export default function Home() {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <main className="flex-1 flex flex-col">
        <ChatInterface />
      </main>
    </div>
  )
}
```

### 3. Test Component Integration
```bash
# Your page should now show a basic layout with sidebar and chat area
# (Components will be empty for now, but the structure should be visible)
```

## 📋 Today's Goals

- [x] Create Next.js project
- [x] Set up project structure
- [x] Create basic types
- [x] Test development server
- [ ] Create basic layout
- [ ] Test component integration

## 🎯 Tomorrow's Goals

- [ ] Implement API client
- [ ] Set up state management
- [ ] Create chat interface
- [ ] Test with your existing backend

## 🚨 Common Issues & Solutions

### Issue: TypeScript path resolution not working
**Solution**: Restart your TypeScript server in VS Code (Cmd+Shift+P → "TypeScript: Restart TS Server")

### Issue: Tailwind classes not applying
**Solution**: Ensure `tailwind.config.ts` includes your source directory:
```typescript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  // ... rest of config
}
```

### Issue: Components not rendering
**Solution**: Check that you're using `'use client'` directive for interactive components

## 🔗 Useful Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Zustand State Management](https://github.com/pmndrs/zustand)
- [React Hook Form](https://react-hook-form.com/)

## 📞 Need Help?

1. Check the browser console for errors
2. Verify all imports are correct
3. Ensure TypeScript compilation passes (`npm run build`)
4. Check that your backend is running on port 9000

---

**You're now ready to start building!** 🎉

The foundation is set up, and you can begin implementing components one by one. Start with the chat interface, then move to the sidebar, and gradually build up the full application.

'use client';

import { Sidebar } from '@/components/sidebar/Sidebar';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { MessageComposer } from '@/components/chat/MessageComposer';

export default function Home() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar />
      <main className="flex-1 flex flex-col">
        <ChatInterface />
        <MessageComposer />
      </main>
    </div>
  );
}

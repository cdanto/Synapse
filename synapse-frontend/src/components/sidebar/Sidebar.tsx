'use client';

import { useState } from 'react';
import { RAGControls } from './RAGControls';
import { KnowledgeBase } from './KnowledgeBase';
import { ChatControls } from './ChatControls';

export function Sidebar() {
  const [activeTab, setActiveTab] = useState<'chat' | 'rag' | 'kb'>('chat');

  return (
    <aside className="w-80 bg-white border-r border-gray-200 p-4 flex flex-col">
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
              onClick={() => setActiveTab(tab.id as 'chat' | 'rag' | 'kb')}
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

      <div className="flex-1 overflow-y-auto">
        {activeTab === 'chat' && <ChatControls />}
        {activeTab === 'rag' && <RAGControls />}
        {activeTab === 'kb' && <KnowledgeBase />}
      </div>
    </aside>
  );
}

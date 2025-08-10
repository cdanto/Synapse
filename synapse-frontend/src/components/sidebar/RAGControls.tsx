'use client';

import { useState, useEffect } from 'react';
import { useConfigStore } from '@/stores/config-store';
import { Switch } from '@/components/ui/Switch';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { apiClient } from '@/lib/api';

export function RAGControls() {
  const { config, updateConfig } = useConfigStore();
  const [isLoading, setIsLoading] = useState(false);
  const [ragStatus, setRagStatus] = useState<boolean | null>(null);

  useEffect(() => {
    // Load current RAG status from backend
    loadRAGStatus();
  }, []);

  const loadRAGStatus = async () => {
    try {
      // We'll get this from the config endpoint
      const backendConfig = await apiClient.getConfig();
      setRagStatus(backendConfig.auto_rag);
    } catch (error) {
      console.error('Failed to load RAG status:', error);
    }
  };

  const handleAutoRAGChange = async (checked: boolean) => {
    setIsLoading(true);
    try {
      await apiClient.setRAGState(checked);
      updateConfig({ auto_rag: checked });
      setRagStatus(checked);
    } catch (error) {
      console.error('Failed to update RAG state:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTopKChange = (value: string) => {
    const topK = parseInt(value);
    if (!isNaN(topK) && topK >= 1 && topK <= 20) {
      updateConfig({ rag_top_k: topK });
    }
  };

  const handleMaxCharsChange = (value: string) => {
    const maxChars = parseInt(value);
    if (!isNaN(maxChars) && maxChars >= 100 && maxChars <= 10000) {
      updateConfig({ rag_max_chars: maxChars });
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">RAG Settings</h3>
        <Button
          variant="outline"
          size="sm"
          onClick={loadRAGStatus}
          disabled={isLoading}
        >
          {isLoading ? 'Loading...' : 'Refresh'}
        </Button>
      </div>
      
      {ragStatus !== null && (
        <div className={`text-sm p-2 rounded-lg ${
          ragStatus ? 'bg-green-50 text-green-700' : 'bg-gray-50 text-gray-700'
        }`}>
          Status: {ragStatus ? 'Enabled' : 'Disabled'}
        </div>
      )}
      
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-700">
            Auto RAG
          </label>
          <Switch
            checked={config.auto_rag}
            onCheckedChange={handleAutoRAGChange}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Top K Results
          </label>
          <Input
            type="number"
            min="1"
            max="20"
            value={config.rag_top_k}
            onChange={(e) => handleTopKChange(e.target.value)}
            className="w-full"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Max Chars per Result
          </label>
          <Input
            type="number"
            min="100"
            max="10000"
            step="100"
            value={config.rag_max_chars}
            onChange={(e) => handleMaxCharsChange(e.target.value)}
            className="w-full"
          />
        </div>

        <div className="text-xs text-gray-500 bg-gray-50 p-3 rounded-lg">
          <p>Auto RAG will automatically search your knowledge base for relevant information when enabled.</p>
        </div>
      </div>
    </div>
  );
}

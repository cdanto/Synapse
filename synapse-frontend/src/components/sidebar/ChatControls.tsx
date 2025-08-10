'use client';

import { useState, useEffect, useCallback } from 'react';
import { useConfigStore } from '@/stores/config-store';
import { useChatStore } from '@/stores/chat-store';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { apiClient } from '@/lib/api';

export function ChatControls() {
  const { config, updateConfig } = useConfigStore();
  const [isLoading, setIsLoading] = useState(false);

  const loadConfig = useCallback(async () => {
    try {
      const backendConfig = await apiClient.getConfig();
      updateConfig(backendConfig);
    } catch (error) {
      console.error('Failed to load config:', error);
    }
  }, [updateConfig]);

  useEffect(() => {
    // Load config from backend on mount
    loadConfig();
  }, [loadConfig]);

  const handleTemperatureChange = async (value: string) => {
    const temp = parseFloat(value);
    if (!isNaN(temp) && temp >= 0 && temp <= 2) {
      updateConfig({ temperature: temp });
      // Sync with backend
      try {
        await apiClient.updateConfig({ temperature: temp });
      } catch (error) {
        console.error('Failed to update temperature:', error);
      }
    }
  };

  const handleMaxTokensChange = async (value: string) => {
    const tokens = parseInt(value);
    if (!isNaN(tokens) && tokens >= 1 && tokens <= 4000) {
      updateConfig({ max_tokens: tokens });
      // Sync with backend
      try {
        await apiClient.updateConfig({ max_tokens: tokens });
      } catch (error) {
        console.error('Failed to update max tokens:', error);
      }
    }
  };

  const { clearChat } = useChatStore();

  const handleClearChat = async () => {
    setIsLoading(true);
    try {
      await apiClient.clearChatHistory();
      clearChat();
    } catch (error) {
      console.error('Failed to clear chat history:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Chat Settings</h3>
      
      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Temperature: {config.temperature}
          </label>
          <input
            type="range"
            min="0"
            max="2"
            step="0.1"
            value={config.temperature}
            onChange={(e) => handleTemperatureChange(e.target.value)}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>Focused</span>
            <span>Creative</span>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Max Tokens
          </label>
          <Input
            type="number"
            min="1"
            max="4000"
            value={config.max_tokens}
            onChange={(e) => handleMaxTokensChange(e.target.value)}
            className="w-full"
          />
        </div>

        <Button
          onClick={handleClearChat}
          variant="outline"
          className="w-full"
          disabled={isLoading}
        >
          {isLoading ? 'Clearing...' : 'Clear Chat'}
        </Button>
      </div>
    </div>
  );
}

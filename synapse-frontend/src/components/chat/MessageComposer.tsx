'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Send, Paperclip, Upload, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useChatStore } from '@/stores/chat-store';
import { useChat } from '@/hooks/use-chat';
import { apiClient } from '@/lib/api';

interface ComposeForm {
  message: string;
}

export function MessageComposer() {
  const { register, handleSubmit, reset, watch } = useForm<ComposeForm>();
  const { addMessage } = useChatStore();
  const { sendMessage, isStreaming } = useChat();
  const message = watch('message');
  const [isAttaching, setIsAttaching] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);

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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(onSubmit)();
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setSelectedFiles(prev => [...prev, ...files]);
  };

  const handleFileDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const files = Array.from(event.dataTransfer.files);
    setSelectedFiles(prev => [...prev, ...files]);
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const uploadFiles = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    try {
      const response = await apiClient.uploadFiles(selectedFiles);
      if (response.success) {
        // Add a system message about the upload
        addMessage({
          role: 'assistant',
          content: `Successfully uploaded ${response.uploaded_files?.length || 0} files to the knowledge base. You can now ask questions about these documents.`,
          timestamp: new Date().toISOString(),
        });
        setSelectedFiles([]);
        setIsAttaching(false);
      } else {
        throw new Error(response.message);
      }
    } catch (error) {
      console.error('Upload error:', error);
      addMessage({
        role: 'assistant',
        content: `Error uploading files: ${error instanceof Error ? error.message : 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="border-t bg-white p-4">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
        <div className="flex space-x-3">
          <div className="flex-1 relative">
            <textarea
              {...register('message')}
              placeholder="Type your message... Shift+Enter for newline"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              rows={3}
              disabled={isStreaming}
              onKeyDown={handleKeyDown}
            />
            <div className="absolute bottom-2 right-2 text-xs text-gray-400">
              Shift+Enter for new line
            </div>
          </div>
          
          <div className="flex flex-col space-y-2">
            <Button
              type="submit" 
              disabled={!message?.trim() || isStreaming}
              className="px-6"
            >
              <Send className="w-4 h-4 mr-2" />
              {isStreaming ? 'Sending...' : 'Send'}
            </Button>
            
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsAttaching(!isAttaching)}
              className="px-6"
            >
              <Paperclip className="w-4 h-4 mr-2" />
              Attach
            </Button>
          </div>
        </div>

        {isAttaching && (
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-4">
            <div className="text-center mb-4">
              <Paperclip className="mx-auto h-8 w-8 text-gray-400 mb-2" />
              <p className="text-sm text-gray-600 mb-2">
                Drag and drop files here, or click to browse
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => document.getElementById('file-input')?.click()}
              >
                Browse Files
              </Button>
              <input
                id="file-input"
                type="file"
                multiple
                accept=".txt,.md,.pdf,.docx,.csv,.json"
                className="hidden"
                onChange={handleFileSelect}
              />
            </div>

            {/* File Drop Zone */}
            <div
              className="border-2 border-dashed border-gray-300 rounded-lg p-4 mb-4"
              onDrop={handleFileDrop}
              onDragOver={handleDragOver}
            >
              <div className="text-center">
                <Upload className="mx-auto h-6 w-6 text-gray-400 mb-2" />
                <p className="text-sm text-gray-600">Drop files here</p>
              </div>
            </div>

            {/* Selected Files */}
            {selectedFiles.length > 0 && (
              <div className="space-y-2">
                <div className="text-sm font-medium text-gray-700">Selected Files:</div>
                {selectedFiles.map((file, index) => (
                  <div key={index} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                    <span className="text-sm text-gray-600 truncate">{file.name}</span>
                    <button
                      onClick={() => removeFile(index)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                
                <div className="flex space-x-2 pt-2">
                  <Button
                    onClick={uploadFiles}
                    disabled={isUploading}
                    className="flex-1"
                  >
                    {isUploading ? 'Uploading...' : 'Upload Files'}
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setSelectedFiles([]);
                      setIsAttaching(false);
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </form>
    </div>
  );
}

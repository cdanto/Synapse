'use client';

import { useState, useEffect } from 'react';
import { Upload, FileText, Trash2, RefreshCw, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { apiClient, KnowledgeBaseStats } from '@/lib/api';

export function KnowledgeBase() {
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [stats, setStats] = useState<KnowledgeBaseStats>({
    total_documents: 0,
    total_chunks: 0,
    index_size_mb: 0,
    last_updated: 'Never'
  });
  const [kbFiles, setKbFiles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadKnowledgeBaseData();
  }, []);

  const loadKnowledgeBaseData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [statsData, filesData] = await Promise.all([
        apiClient.getKnowledgeBaseStats(),
        apiClient.getKnowledgeBaseFiles()
      ]);
      setStats(statsData);
      setKbFiles(filesData);
    } catch (error) {
      console.error('Failed to load knowledge base data:', error);
      setError('Failed to load knowledge base data');
    } finally {
      setIsLoading(false);
    }
  };

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
      const response = await apiClient.uploadFiles(files);
      if (response.success) {
        setFiles([]);
        // Reload the knowledge base data
        await loadKnowledgeBaseData();
      } else {
        throw new Error(response.message);
      }
    } catch (error) {
      console.error('Upload failed:', error);
      setError(`Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsUploading(false);
    }
  };

  const reloadKB = async () => {
    try {
      await apiClient.kbReload();
      await loadKnowledgeBaseData();
    } catch (error) {
      console.error('KB reload failed:', error);
      setError('Failed to reload knowledge base');
    }
  };

  const deleteFile = async (filename: string) => {
    try {
      await apiClient.deleteKnowledgeBaseFile(filename);
      await loadKnowledgeBaseData();
    } catch (error) {
      console.error('File deletion failed:', error);
      setError('Failed to delete file');
    }
  };

  const clearKnowledgeBase = async () => {
    if (!confirm('Are you sure you want to clear the entire knowledge base? This action cannot be undone.')) {
      return;
    }
    
    try {
      await apiClient.clearKnowledgeBase();
      await loadKnowledgeBaseData();
    } catch (error) {
      console.error('Knowledge base clear failed:', error);
      setError('Failed to clear knowledge base');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Knowledge Base</h3>
        <Button
          onClick={reloadKB}
          variant="outline"
          size="sm"
          disabled={isLoading}
        >
          <RefreshCw className={`w-4 h-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
          Reload
        </Button>
      </div>

      {error && (
        <div className="flex items-center space-x-2 p-3 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="w-4 h-4 text-red-500" />
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {/* Stats */}
      <div className="bg-gray-50 p-3 rounded-lg space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Documents:</span>
          <span className="font-medium">{stats.total_documents}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Chunks:</span>
          <span className="font-medium">{stats.total_chunks}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Index Size:</span>
          <span className="font-medium">{stats.index_size_mb} MB</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">Last Updated:</span>
          <span className="font-medium">{stats.last_updated}</span>
        </div>
      </div>

      {/* File Upload */}
      <div className="space-y-3">
        <h4 className="font-medium text-gray-900">Upload Files</h4>
        
        <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center">
          <Upload className="mx-auto h-8 w-8 text-gray-400 mb-2" />
          <Button
            variant="outline"
            onClick={() => document.getElementById('file-input')?.click()}
            disabled={isUploading}
            size="sm"
          >
            Select Files
          </Button>
          <input
            id="file-input"
            type="file"
            multiple
            accept=".txt,.md,.pdf,.docx,.csv,.json"
            onChange={handleFileSelect}
            className="hidden"
          />
        </div>

        {files.length > 0 && (
          <div className="space-y-2">
            <h5 className="text-sm font-medium text-gray-700">Selected Files:</h5>
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
                  <Trash2 className="h-4 w-4" />
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

      {/* Knowledge Base Files */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="font-medium text-gray-900">Files ({kbFiles.length})</h4>
          {kbFiles.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={clearKnowledgeBase}
              className="text-red-600 hover:text-red-700"
            >
              Clear All
            </Button>
          )}
        </div>

        {kbFiles.length === 0 ? (
          <div className="text-center py-4 text-gray-500">
            <FileText className="mx-auto h-8 w-8 text-gray-300 mb-2" />
            <p className="text-sm">No files uploaded yet</p>
          </div>
        ) : (
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {kbFiles.map((filename, index) => (
              <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                <div className="flex items-center space-x-2">
                  <FileText className="h-4 w-4 text-gray-500" />
                  <span className="text-sm truncate">{filename}</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteFile(filename)}
                  className="text-red-500 hover:text-red-700"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

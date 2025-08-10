import { create } from 'zustand';
import { KnowledgeBaseStats, UploadResponse } from '@/types';
import { apiClient } from '@/lib/api-client';

interface KBStore {
  stats: KnowledgeBaseStats | null;
  isLoading: boolean;
  error: string | null;
  isUploading: boolean;
  
  // Actions
  fetchStats: () => Promise<void>;
  reloadKB: () => Promise<void>;
  uploadFiles: (files: File[]) => Promise<UploadResponse>;
  clearKB: () => Promise<void>;
  resetError: () => void;
}

export const useKBStore = create<KBStore>((set, get) => ({
  stats: null,
  isLoading: false,
  error: null,
  isUploading: false,

  fetchStats: async () => {
    set({ isLoading: true, error: null });
    try {
      const stats = await apiClient.getKBStats();
      set({ stats, isLoading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to fetch KB stats',
        isLoading: false 
      });
    }
  },

  reloadKB: async () => {
    set({ isLoading: true, error: null });
    try {
      await apiClient.reloadKB();
      // Refresh stats after reload
      const stats = await apiClient.getKBStats();
      set({ stats, isLoading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to reload KB',
        isLoading: false 
      });
    }
  },

  uploadFiles: async (files) => {
    set({ isUploading: true, error: null });
    try {
      const result = await apiClient.uploadFiles(files);
      // Refresh stats after upload
      const stats = await apiClient.getKBStats();
      set({ stats, isUploading: false });
      return result;
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to upload files',
        isUploading: false 
      });
      throw error;
    }
  },

  clearKB: async () => {
    set({ isLoading: true, error: null });
    try {
      await apiClient.clearKB();
      set({ stats: null, isLoading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to clear KB',
        isLoading: false 
      });
    }
  },

  resetError: () => set({ error: null }),
}));

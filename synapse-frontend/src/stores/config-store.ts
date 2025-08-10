import { create } from 'zustand';
import { Config } from '@/types';

interface ConfigStore {
  config: Config;
  updateConfig: (updates: Partial<Config>) => void;
  resetConfig: () => void;
}

const defaultConfig: Config = {
  temperature: 0.7,
  top_p: 0.9,
  max_tokens: 1000,
  auto_rag: true,
  rag_top_k: 5,
  rag_max_chars: 1000,
};

export const useConfigStore = create<ConfigStore>((set) => ({
  config: defaultConfig,

  updateConfig: (updates) =>
    set((state) => ({
      config: { ...state.config, ...updates },
    })),

  resetConfig: () =>
    set({ config: defaultConfig }),
}));

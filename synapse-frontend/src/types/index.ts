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
  relevance_score?: number;
  confidence?: string;
  chunk_id?: string;
  page?: string;
  section?: string;
  word_count?: number;
  vector_score?: number;
  bm25_score?: number;
  title_boost?: number;
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

export interface KnowledgeBaseStats {
  total_documents: number;
  total_chunks: number;
  index_size_mb: number;
  last_updated: string;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  uploaded_files?: string[];
  errors?: string[];
}

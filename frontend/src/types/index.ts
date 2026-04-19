// 聊天消息类型
export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: Source[];
  relevanceScore?: number;
  reasoning?: string[];  // 后端返回的是字符串数组
}

// 来源文档
export interface Source {
  id: string;
  filename: string;
  page?: number;
  chunk?: string;
  relevance: number;
}

// 会话历史
export interface Conversation {
  id: string;
  title: string;
  preview: string;
  timestamp: string;
  messageCount: number;
}

// 文档类型
export interface Document {
  id: string;
  filename: string;
  uploadTime: string;
  status: 'processing' | 'completed' | 'failed';
  size: number;
  type: string;
}

// 知识库文档类型（从向量数据库中获取）
export interface KbDocument {
  doc_id: string;
  filename: string;
  mime_type: string;
  ingested_at: string;
  chunk_count: number;
  metadata?: Record<string, any>;
}

// 知识库状态
export interface KnowledgeBaseStatus {
  totalDocuments: number;
  totalChunks: number;
  vectorStatus: 'healthy' | 'warning' | 'error';
  lastUpdated: string;
}

// 操作日志
export interface OperationLog {
  id: string;
  operation: string;
  status: 'success' | 'failed' | 'pending';
  timestamp: string;
  details?: string;
}

// API响应类型
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  deleted_count?: number;
  failed_ids?: string[];
}

// 聊天请求
export interface ChatRequest {
  message: string;
  conversationId?: string;
  sessionId?: string;
  attachment_ids?: string[];
}

// 聊天响应
export interface ChatResponse {
  answer: string;
  sources: Source[];
  relevanceScore?: number;
  confidence?: number;
  reasoning?: string[];
  conversationId?: string;
  messageId?: string;
  sessionId?: string;
  metadata?: Record<string, any>;
  error?: string | null;
}

// 上传进度
export interface UploadProgress {
  filename: string;
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
}

// 系统设置
export interface Settings {
  api: {
    baseUrl: string;
    timeout: number;
  };
  model: {
    embeddingModel: string;
    llmModel: string;
    temperature: number;
    maxTokens: number;
  };
  ui: {
    theme: 'light' | 'dark';
    language: 'zh' | 'en';
    fontSize: 'small' | 'medium' | 'large';
  };
  search: {
    defaultTopK: number;
    fusionMethod: 'rrf' | 'weighted' | 'simple';
    vectorWeight: number;
    keywordWeight: number;
  };
}

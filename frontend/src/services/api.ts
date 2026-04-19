import axios from 'axios';
import type {
  ApiResponse,
  ChatRequest,
  ChatResponse,
  Document,
  KbDocument,
  KnowledgeBaseStatus,
  OperationLog,
} from '@/types';
import { errorHandler, AppError } from '@/utils/errorHandler';

// API 配置
const API_CONFIG = {
  // 使用相对路径，由 Vite 代理（开发环境）或反向代理（生产环境）处理
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: Number(import.meta.env.VITE_API_TIMEOUT) || 180000, // 3分钟默认超时
  enableRetry: true,
  maxRetries: 3,
  retryDelay: 1000,
};

// 创建 axios 实例
const api = axios.create({
  baseURL: API_CONFIG.baseURL,
  timeout: API_CONFIG.timeout,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 重试拦截器
const retryInterceptor = (error: any) => {
  if (!API_CONFIG.enableRetry) return Promise.reject(error);

  const config = error.config;
  if (!config) return Promise.reject(error);

  const retries = config.__retryCount || 0;

  if (retries >= API_CONFIG.maxRetries) {
    return Promise.reject(error);
  }

  config.__retryCount = retries + 1;

  return new Promise((resolve) => {
    setTimeout(() => resolve(api(config)), API_CONFIG.retryDelay * retries);
  });
};

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 从 localStorage 获取设置
    const settings = localStorage.getItem('app-settings');
    if (settings) {
      const parsedSettings = JSON.parse(settings);
      if (parsedSettings.api?.timeout) {
        config.timeout = parsedSettings.api.timeout;
      }
    }

    // 添加 token（如果有）
    const token = localStorage.getItem('auth-token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // 添加请求 ID 用于追踪
    config.headers['X-Request-ID'] = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    // 检查业务状态码
    const data = response.data;
    if (data && typeof data === 'object' && 'success' in data) {
      if (!data.success && data.error) {
        // 业务逻辑错误
        throw new AppError(
          data.error,
          'API_ERROR',
          data.code,
          response.status,
          data
        );
      }
    }
    return response.data;
  },
  async (error) => {
    const originalRequest = error.config;

    // 网络错误或超时
    if (!error.response) {
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        // 尝试重试
        if (!originalRequest.__isRetry) {
          originalRequest.__isRetry = true;
          return retryInterceptor(error);
        }
        throw new AppError('请求超时，请检查网络连接', 'NETWORK_ERROR');
      }
      throw new AppError('网络连接失败，请检查您的网络', 'NETWORK_ERROR');
    }

    // HTTP 错误状态
    const status = error.response.status;
    const data = error.response.data;

    // 401 未授权 - 可能需要重新登录
    if (status === 401 && !originalRequest.__isRetry) {
      originalRequest.__isRetry = true;
      // 这里可以添加刷新 token 的逻辑
      // 暂时直接抛出错误
      throw new AppError(
        data?.message || '权限不足或登录已过期',
        'AUTH_ERROR',
        data?.code,
        status
      );
    }

    // 403 禁止访问
    if (status === 403) {
      throw new AppError(
        data?.message || '没有权限访问此资源',
        'AUTH_ERROR',
        data?.code,
        status
      );
    }

    // 404 未找到
    if (status === 404) {
      throw new AppError(
        data?.message || '请求的资源不存在',
        'API_ERROR',
        data?.code,
        status
      );
    }

    // 422/400 验证错误
    if (status === 422 || status === 400) {
      throw new AppError(
        data?.message || '请求数据有误',
        'VALIDATION_ERROR',
        data?.code,
        status,
        data?.details
      );
    }

    // 5xx 服务器错误 - 尝试重试
    if (status >= 500 && !originalRequest.__isRetry) {
      originalRequest.__isRetry = true;
      return retryInterceptor(error);
    }

    // 其他错误
    throw new AppError(
      data?.message || error.message || '请求失败',
      'API_ERROR',
      data?.code,
      status
    );
  }
);

// 封装 API 调用，自动处理错误
const apiCall = async <T>(
  fn: () => Promise<T>,
  showErrorToast = true
): Promise<T> => {
  try {
    return await fn();
  } catch (error) {
    throw errorHandler.handle(error, showErrorToast);
  }
};

// 聊天相关 API
export const chatApi = {
  // 发送消息
  sendMessage: async (data: ChatRequest): Promise<ApiResponse<ChatResponse>> => {
    return apiCall(() => api.post('/chat', data));
  },

  // 获取会话历史
  getConversations: async (): Promise<ApiResponse> => {
    return apiCall(() => api.get('/conversations'), false);
  },

  // 删除会话
  deleteConversation: async (conversationId: string): Promise<ApiResponse> => {
    return apiCall(() => api.delete(`/conversations/${conversationId}`), false);
  },

  // 批量删除会话
  batchDeleteConversations: async (conversationIds: string[]): Promise<ApiResponse> => {
    return apiCall(() =>
      api.delete('/conversations/batch', { data: { ids: conversationIds } }), false
    );
  },

  // 获取会话详情
  getConversationMessages: async (conversationId: string): Promise<ApiResponse> => {
    return apiCall(() => api.get(`/conversations/${conversationId}/messages`), false);
  },
};

// 文档管理 API
export const documentApi = {
  // 上传文档
  uploadDocument: async (
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<ApiResponse> => {
    return apiCall(() => {
      const formData = new FormData();
      formData.append('file', file);

      return api.post('/documents/ingest', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress(progress);
          }
        },
      });
    });
  },

  // 获取文档列表
  getDocuments: async (): Promise<ApiResponse<Document[]>> => {
    return apiCall(() => api.get('/documents'));
  },

  // 删除文档
  deleteDocument: async (documentId: string): Promise<ApiResponse> => {
    return apiCall(() => api.delete(`/documents/${documentId}`));
  },

  // 批量删除文档
  batchDeleteDocuments: async (documentIds: string[]): Promise<ApiResponse> => {
    return apiCall(() =>
      api.delete('/documents/batch', { data: { ids: documentIds } })
    );
  },

  // 重新处理文档
  reprocessDocument: async (documentId: string): Promise<ApiResponse> => {
    return apiCall(() => api.post(`/documents/${documentId}/reprocess`));
  },
};

// 知识库管理 API
export const knowledgeBaseApi = {
  // 获取知识库状态
  getStatus: async (): Promise<ApiResponse<KnowledgeBaseStatus>> => {
    return apiCall(() => api.get('/kb/status'));
  },

  // 获取知识库中的文档列表
  getDocuments: async (): Promise<ApiResponse<KbDocument[]>> => {
    return apiCall(() => api.get('/documents/list'));
  },

  // 删除知识库中的文档
  deleteDocument: async (docId: string): Promise<ApiResponse> => {
    return apiCall(() => api.delete(`/documents/${docId}`));
  },

  // 清空知识库
  clearKnowledgeBase: async (): Promise<ApiResponse> => {
    return apiCall(() => api.delete('/kb/clear'));
  },

  // 重置向量库
  resetVectorStore: async (): Promise<ApiResponse> => {
    return apiCall(() => api.post('/kb/reset'));
  },

  // 获取操作日志
  getOperationLogs: async (limit = 10): Promise<ApiResponse<OperationLog[]>> => {
    return apiCall(() => api.get(`/kb/logs?limit=${limit}`));
  },
};

// 搜索 API（新增）
export const searchApi = {
  // 混合搜索
  hybridSearch: async (query: string, options?: {
    top_k?: number;
    fusion_method?: 'rrf' | 'weighted' | 'simple';
    vector_weight?: number;
    keyword_weight?: number;
  }): Promise<ApiResponse> => {
    return apiCall(() =>
      api.post('/search/hybrid', {
        query,
        top_k: options?.top_k || 10,
        fusion_method: options?.fusion_method || 'rrf',
        vector_weight: options?.vector_weight || 0.7,
        keyword_weight: options?.keyword_weight || 0.3,
      })
    );
  },

  // 向量搜索
  vectorSearch: async (query: string, topK = 10): Promise<ApiResponse> => {
    return apiCall(() =>
      api.post('/search', {
        query,
        top_k: topK,
      })
    );
  },
};

// 附件 API
export const attachmentApi = {
  // 上传临时附件
  upload: async (file: File, sessionId: string): Promise<ApiResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);

    return apiCall(() =>
      api.post('/chat/attachments/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
    );
  },

  // 获取会话的附件列表
  list: async (sessionId: string): Promise<ApiResponse> => {
    return apiCall(() => api.get(`/chat/attachments/list/${sessionId}`));
  },

  // 删除附件
  delete: async (attachmentId: string, sessionId: string): Promise<ApiResponse> => {
    return apiCall(() => api.delete(`/chat/attachments/delete/${attachmentId}?session_id=${sessionId}`));
  },

  // 清理会话的所有附件
  cleanup: async (sessionId: string): Promise<ApiResponse> => {
    return apiCall(() => api.delete(`/chat/attachments/cleanup/${sessionId}`));
  },
};

// 健康检查 API
export const healthApi = {
  // 检查后端健康状态
  check: async (): Promise<{ status: string; timestamp: string }> => {
    return apiCall(() => api.get('/health'), false);
  },
};

// 设置错误处理器的 Toast 处理函数
export const setupErrorHandler = (
  showToast: (type: 'success' | 'error' | 'warning' | 'info', message: string) => void
) => {
  errorHandler.setToastHandler(showToast);
};

export default api;
export { API_CONFIG };


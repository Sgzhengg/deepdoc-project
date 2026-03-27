/**
 * 全局错误处理工具
 */

import type { ToastType } from '@/components/Common';

export interface ErrorInfo {
  message: string;
  code?: string;
  status?: number;
  details?: any;
}

/**
 * 错误类型枚举
 */
export enum ErrorType {
  NETWORK = 'NETWORK_ERROR',
  API = 'API_ERROR',
  VALIDATION = 'VALIDATION_ERROR',
  AUTH = 'AUTH_ERROR',
  UNKNOWN = 'UNKNOWN_ERROR',
}

/**
 * 错误类
 */
export class AppError extends Error {
  type: ErrorType;
  code?: string;
  status?: number;
  details?: any;

  constructor(
    message: string,
    type: ErrorType = ErrorType.UNKNOWN,
    code?: string,
    status?: number,
    details?: any
  ) {
    super(message);
    this.name = 'AppError';
    this.type = type;
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

/**
 * 错误处理器类
 */
export class ErrorHandler {
  private static instance: ErrorHandler;
  private showToast?: (type: ToastType, message: string) => void;

  private constructor() {}

  static getInstance(): ErrorHandler {
    if (!ErrorHandler.instance) {
      ErrorHandler.instance = new ErrorHandler();
    }
    return ErrorHandler.instance;
  }

  /**
   * 设置 Toast 显示函数
   */
  setToastHandler(handler: (type: ToastType, message: string) => void) {
    this.showToast = handler;
  }

  /**
   * 处理错误
   */
  handle(error: unknown, showToast = true): AppError {
    let appError: AppError;

    if (error instanceof AppError) {
      appError = error;
    } else if (error instanceof Error) {
      appError = new AppError(error.message, ErrorType.UNKNOWN);
    } else if (typeof error === 'string') {
      appError = new AppError(error);
    } else {
      appError = new AppError('发生了未知错误');
    }

    // 记录错误
    this.logError(appError);

    // 显示 Toast
    if (showToast && this.showToast) {
      this.showToastForError(appError);
    }

    return appError;
  }

  /**
   * 根据 API 响应创建错误
   */
  fromApiResponse(response: any): AppError {
    const message = response?.error || response?.message || '请求失败';
    const code = response?.code;
    const status = response?.status;

    let type = ErrorType.API;
    if (status === 401 || status === 403) {
      type = ErrorType.AUTH;
    } else if (status === 400) {
      type = ErrorType.VALIDATION;
    } else if (status >= 500) {
      type = ErrorType.UNKNOWN;
    }

    return new AppError(message, type, code, status, response);
  }

  /**
   * 显示错误 Toast
   */
  private showToastForError(error: AppError) {
    if (!this.showToast) return;

    let type: ToastType = 'error';
    let message = error.message;

    switch (error.type) {
      case ErrorType.NETWORK:
        message = '网络连接失败，请检查您的网络';
        type = 'warning';
        break;
      case ErrorType.AUTH:
        message = '权限不足或登录已过期';
        type = 'warning';
        break;
      case ErrorType.VALIDATION:
        message = error.message || '输入数据有误';
        break;
      default:
        message = error.message || '操作失败，请稍后重试';
    }

    this.showToast(type, message);
  }

  /**
   * 记录错误到控制台和日志
   */
  private logError(error: AppError) {
    console.error('[ErrorHandler]', error);

    // 存储到 localStorage 用于调试
    try {
      const errorLogs = JSON.parse(localStorage.getItem('error-logs') || '[]');
      errorLogs.push({
        type: error.type,
        message: error.message,
        code: error.code,
        status: error.status,
        timestamp: new Date().toISOString(),
      });
      // 只保留最近 50 条
      if (errorLogs.length > 50) errorLogs.shift();
      localStorage.setItem('error-logs', JSON.stringify(errorLogs));
    } catch (e) {
      // 忽略存储错误
    }
  }

  /**
   * 获取错误日志
   */
  getErrorLogs(): any[] {
    try {
      return JSON.parse(localStorage.getItem('error-logs') || '[]');
    } catch {
      return [];
    }
  }

  /**
   * 清除错误日志
   */
  clearErrorLogs() {
    localStorage.removeItem('error-logs');
  }
}

// 导出单例实例
export const errorHandler = ErrorHandler.getInstance();

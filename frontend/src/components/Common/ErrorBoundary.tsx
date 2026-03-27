import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // 记录错误到日志服务
    this.logErrorToService(error, errorInfo);

    // 调用自定义错误处理函数
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    this.setState({
      error,
      errorInfo,
    });
  }

  logErrorToService = (error: Error, errorInfo: ErrorInfo) => {
    // 这里可以集成错误日志服务，如 Sentry
    const errorData = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
    };

    // 示例：存储到 localStorage
    try {
      const errorLogs = JSON.parse(localStorage.getItem('error-logs') || '[]');
      errorLogs.push(errorData);
      // 只保留最近 50 条错误日志
      if (errorLogs.length > 50) {
        errorLogs.shift();
      }
      localStorage.setItem('error-logs', JSON.stringify(errorLogs));
    } catch (e) {
      console.error('Failed to save error log:', e);
    }
  };

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义 fallback，使用它
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // 默认错误 UI
      return (
        <div className="min-h-screen bg-chat-bg flex items-center justify-center p-4">
          <div className="max-w-lg w-full bg-chat-bg-secondary rounded-lg border border-chat-border p-6">
            <div className="flex items-center gap-3 mb-4">
              <AlertTriangle size={32} className="text-red-400" />
              <h1 className="text-xl font-semibold text-chat-text">
                出错了
              </h1>
            </div>

            <p className="text-gray-300 mb-4">
              很抱歉，应用程序遇到了一个错误。请尝试刷新页面或联系支持团队。
            </p>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mb-4">
                <summary className="cursor-pointer text-sm text-chat-accent mb-2">
                  查看错误详情
                </summary>
                <div className="mt-2 p-3 bg-chat-bg rounded border border-chat-border">
                  <p className="text-sm text-red-400 font-mono mb-2">
                    {this.state.error.toString()}
                  </p>
                  {this.state.errorInfo && (
                    <pre className="text-xs text-gray-400 overflow-x-auto">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              </details>
            )}

            <div className="flex gap-3">
              <button
                onClick={this.handleReset}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-chat-input hover:bg-chat-bg text-chat-text rounded-lg border border-chat-border transition-colors"
              >
                <RefreshCw size={16} />
                <span>重试</span>
              </button>
              <button
                onClick={this.handleReload}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-chat-accent hover:bg-chat-accent/90 text-white rounded-lg transition-colors"
              >
                <span>刷新页面</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Hook 版本的错误边界（用于函数组件）
export const useErrorHandler = () => {
  return (error: Error) => {
    throw error;
  };
};

export default ErrorBoundary;

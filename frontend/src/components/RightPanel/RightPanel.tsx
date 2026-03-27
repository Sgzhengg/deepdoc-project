import React, { useEffect, useState, useRef } from 'react';
import { Upload, File, Trash2, RefreshCw, Database, FileText, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { useStore } from '@/store/useStore';
import { documentApi, knowledgeBaseApi } from '@/services/api';
import type { Document, OperationLog, UploadProgress } from '@/types';

const RightPanel: React.FC = () => {
  const {
    documents,
    setDocuments,
    kbStatus,
    setKbStatus,
    selectedDocuments,
    toggleDocumentSelection,
    clearDocumentSelection,
    setRightPanelOpen,
  } = useStore();

  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [operationLogs, setOperationLogs] = useState<OperationLog[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadDocuments();
    loadKbStatus();
    loadOperationLogs();
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await documentApi.getDocuments();
      if (response.success && response.data) {
        setDocuments(response.data);
      }
    } catch (error) {
      console.error('加载文档列表失败:', error);
    }
  };

  const loadKbStatus = async () => {
    try {
      const response = await knowledgeBaseApi.getStatus();
      if (response.success && response.data) {
        setKbStatus(response.data);
      }
    } catch (error) {
      console.error('加载知识库状态失败:', error);
    }
  };

  const loadOperationLogs = async () => {
    try {
      const response = await knowledgeBaseApi.getOperationLogs(10);
      if (response.success && response.data) {
        setOperationLogs(response.data);
      }
    } catch (error) {
      console.error('加载操作日志失败:', error);
    }
  };

  const handleFileSelect = (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const file = files[0];
    const validTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'];

    if (!validTypes.includes(file.type)) {
      alert('仅支持 PDF、DOCX、XLSX、XLS 格式的文件');
      return;
    }

    uploadFile(file);
  };

  const uploadFile = async (file: File) => {
    setUploadProgress({
      filename: file.name,
      progress: 0,
      status: 'uploading',
    });

    try {
      await documentApi.uploadDocument(file, (progress) => {
        setUploadProgress({
          filename: file.name,
          progress,
          status: progress < 100 ? 'uploading' : 'processing',
        });
      });

      setUploadProgress({
        filename: file.name,
        progress: 100,
        status: 'completed',
      });

      setTimeout(() => {
        setUploadProgress(null);
        loadDocuments();
        loadKbStatus();
      }, 2000);
    } catch (error) {
      setUploadProgress({
        filename: file.name,
        progress: 0,
        status: 'failed',
      });
      setTimeout(() => setUploadProgress(null), 3000);
      alert('上传失败: ' + (error as Error).message);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const handleDeleteDocument = async (documentId: string) => {
    if (!window.confirm('确定要删除这个文档吗？')) return;

    try {
      await documentApi.deleteDocument(documentId);
      loadDocuments();
      loadKbStatus();
    } catch (error) {
      console.error('删除文档失败:', error);
      alert('删除失败');
    }
  };

  const handleBatchDelete = async () => {
    if (selectedDocuments.length === 0) {
      alert('请先选择要删除的文档');
      return;
    }

    if (!window.confirm(`确定要删除选中的 ${selectedDocuments.length} 个文档吗？`)) return;

    try {
      await documentApi.batchDeleteDocuments(selectedDocuments);
      clearDocumentSelection();
      loadDocuments();
      loadKbStatus();
    } catch (error) {
      console.error('批量删除失败:', error);
      alert('删除失败');
    }
  };

  const handleClearKnowledgeBase = async () => {
    if (!window.confirm('确定要清空知识库吗？此操作不可恢复！')) return;

    if (!window.confirm('再次确认：清空知识库将删除所有文档和数据！')) return;

    try {
      await knowledgeBaseApi.clearKnowledgeBase();
      alert('知识库已清空');
      loadDocuments();
      loadKbStatus();
      loadOperationLogs();
    } catch (error) {
      console.error('清空知识库失败:', error);
      alert('操作失败');
    }
  };

  const handleResetVectorStore = async () => {
    if (!window.confirm('确定要重置向量库吗？此操作将重新索引所有文档！')) return;

    try {
      await knowledgeBaseApi.resetVectorStore();
      alert('向量库重置成功，正在重新索引...');
      loadKbStatus();
      loadOperationLogs();
    } catch (error) {
      console.error('重置向量库失败:', error);
      alert('操作失败');
    }
  };

  const getStatusIcon = (status: Document['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={16} className="text-green-400" />;
      case 'processing':
        return <RefreshCw size={16} className="text-yellow-400 animate-spin" />;
      case 'failed':
        return <XCircle size={16} className="text-red-400" />;
    }
  };

  const getStatusText = (status: Document['status']) => {
    switch (status) {
      case 'completed':
        return '已入库';
      case 'processing':
        return '处理中';
      case 'failed':
        return '失败';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="h-full flex flex-col bg-chat-bg-secondary overflow-hidden">
      {/* 标题 */}
      <div className="p-4 border-b border-chat-border">
        <h2 className="text-lg font-semibold text-chat-text">文档管理</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* 文档上传区域 */}
        <div>
          <h3 className="text-sm font-medium text-gray-400 mb-3">上传文档</h3>
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
              dragOver
                ? 'border-chat-accent bg-chat-accent/10'
                : 'border-chat-border hover:border-chat-accent hover:bg-chat-bg-secondary'
            }`}
          >
            <Upload size={32} className="mx-auto mb-3 text-gray-400" />
            <p className="text-sm text-gray-300 mb-2">
              拖拽文件到此处，或点击选择文件
            </p>
            <p className="text-xs text-gray-500">
              支持 PDF、DOCX、XLSX、XLS 格式
            </p>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".pdf,.docx,.xlsx,.xls"
              onChange={(e) => handleFileSelect(e.target.files)}
            />
          </div>

          {/* 上传进度 */}
          {uploadProgress && (
            <div className="mt-3 p-3 bg-chat-bg rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-300 truncate">
                  {uploadProgress.filename}
                </span>
                <span className="text-xs text-gray-400">
                  {uploadProgress.progress}%
                </span>
              </div>
              <div className="w-full bg-chat-input rounded-full h-2 overflow-hidden">
                <div
                  className="bg-chat-accent h-full transition-all duration-300"
                  style={{ width: `${uploadProgress.progress}%` }}
                />
              </div>
              <p className="text-xs text-gray-400 mt-2">
                {uploadProgress.status === 'uploading' && '上传中...'}
                {uploadProgress.status === 'processing' && '处理中...'}
                {uploadProgress.status === 'completed' && '上传完成'}
                {uploadProgress.status === 'failed' && '上传失败'}
              </p>
            </div>
          )}
        </div>

        {/* 已上传文档列表 */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-400">已上传文档</h3>
            {selectedDocuments.length > 0 && (
              <button
                onClick={handleBatchDelete}
                className="text-xs px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
              >
                删除选中 ({selectedDocuments.length})
              </button>
            )}
          </div>

          <div className="space-y-2">
            {documents.length === 0 ? (
              <div className="text-center text-gray-400 py-8 text-sm">
                暂无文档
              </div>
            ) : (
              documents.map((doc) => (
                <div
                  key={doc.id}
                  className={`p-3 bg-chat-bg rounded-lg border border-chat-border hover:border-chat-accent transition-colors ${
                    selectedDocuments.includes(doc.id) ? 'ring-2 ring-chat-accent' : ''
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selectedDocuments.includes(doc.id)}
                      onChange={() => toggleDocumentSelection(doc.id)}
                      className="mt-1"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <File size={16} className="text-gray-400 flex-shrink-0" />
                        <h4 className="text-sm font-medium text-gray-200 truncate">
                          {doc.filename}
                        </h4>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-gray-400">
                        <span>{formatFileSize(doc.size)}</span>
                        <span>{new Date(doc.uploadTime).toLocaleString('zh-CN')}</span>
                        <div className="flex items-center gap-1">
                          {getStatusIcon(doc.status)}
                          <span>{getStatusText(doc.status)}</span>
                        </div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteDocument(doc.id)}
                      className="p-1 hover:bg-chat-bg-secondary rounded transition-colors"
                      title="删除文档"
                    >
                      <Trash2 size={14} className="text-red-400" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 知识库管理 */}
        <div>
          <h3 className="text-sm font-medium text-gray-400 mb-3">知识库管理</h3>

          {/* 统计卡片 */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="p-3 bg-chat-bg rounded-lg border border-chat-border">
              <div className="flex items-center gap-2 mb-1">
                <FileText size={16} className="text-chat-accent" />
                <span className="text-xs text-gray-400">总文档数</span>
              </div>
              <p className="text-xl font-semibold text-chat-text">
                {kbStatus?.totalDocuments || 0}
              </p>
            </div>

            <div className="p-3 bg-chat-bg rounded-lg border border-chat-border">
              <div className="flex items-center gap-2 mb-1">
                <Database size={16} className="text-chat-accent" />
                <span className="text-xs text-gray-400">数据块数</span>
              </div>
              <p className="text-xl font-semibold text-chat-text">
                {kbStatus?.totalChunks || 0}
              </p>
            </div>
          </div>

          {/* 向量库状态 */}
          {kbStatus && (
            <div className="mb-4 p-3 bg-chat-bg rounded-lg border border-chat-border">
              <div className="flex items-center gap-2">
                {kbStatus.vectorStatus === 'healthy' && (
                  <CheckCircle size={16} className="text-green-400" />
                )}
                {kbStatus.vectorStatus === 'warning' && (
                  <AlertCircle size={16} className="text-yellow-400" />
                )}
                {kbStatus.vectorStatus === 'error' && (
                  <XCircle size={16} className="text-red-400" />
                )}
                <span className="text-sm text-gray-300">向量库状态：</span>
                <span className="text-sm font-medium text-gray-200">
                  {kbStatus.vectorStatus === 'healthy' && '正常'}
                  {kbStatus.vectorStatus === 'warning' && '警告'}
                  {kbStatus.vectorStatus === 'error' && '错误'}
                </span>
              </div>
            </div>
          )}

          {/* 操作按钮 */}
          <div className="space-y-2 mb-4">
            <button
              onClick={handleClearKnowledgeBase}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              <Trash2 size={16} />
              <span>清空知识库</span>
            </button>
            <button
              onClick={handleResetVectorStore}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors"
            >
              <RefreshCw size={16} />
              <span>重置向量库</span>
            </button>
          </div>

          {/* 操作日志 */}
          <div>
            <h4 className="text-xs font-medium text-gray-400 mb-2">操作日志</h4>
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {operationLogs.length === 0 ? (
                <div className="text-center text-gray-500 py-4 text-xs">
                  暂无日志
                </div>
              ) : (
                operationLogs.map((log) => (
                  <div
                    key={log.id}
                    className="p-2 bg-chat-bg rounded text-xs border border-chat-border"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-gray-300">{log.operation}</span>
                      <div className="flex items-center gap-1">
                        {log.status === 'success' && (
                          <CheckCircle size={12} className="text-green-400" />
                        )}
                        {log.status === 'failed' && (
                          <XCircle size={12} className="text-red-400" />
                        )}
                        {log.status === 'pending' && (
                          <RefreshCw size={12} className="text-yellow-400 animate-spin" />
                        )}
                      </div>
                    </div>
                    <div className="text-gray-500">
                      {new Date(log.timestamp).toLocaleString('zh-CN')}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RightPanel;

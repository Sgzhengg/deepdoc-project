import React, { useState, useEffect } from 'react';
import {
  Settings,
  FileText,
  Database,
  Trash2,
  Upload,
  RefreshCw,
  ChevronRight,
  List,
  X,
  Calendar
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { documentApi, knowledgeBaseApi } from '@/services/api';
import { Modal } from '@/components/Common';
import type { Document, KbDocument } from '@/types';

const RightSidebar: React.FC = () => {
  const { rightPanelOpen, setRightPanelOpen } = useStore();
  const [activeSection, setActiveSection] = useState<'documents' | 'knowledge' | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [kbStatus, setKbStatus] = useState<any>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set());
  const [showDocListModal, setShowDocListModal] = useState(false);
  const [kbDocuments, setKbDocuments] = useState<KbDocument[]>([]);
  const [loadingDocList, setLoadingDocList] = useState(false);

  useEffect(() => {
    if (rightPanelOpen) {
      loadDocuments();
      loadKbStatus();
    }
  }, [rightPanelOpen]);

  const loadDocuments = async () => {
    try {
      const response = await documentApi.getDocuments();
      if (response.success && response.data) {
        setDocuments(response.data);
      }
    } catch (error) {
      console.error('加载文档失败:', error);
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

  const handleFileUpload = async (files: FileList) => {
    console.log('=== 开始文件上传检查 ===');
    console.log('当前文档列表:', documents);
    console.log('待上传文件:', Array.from(files).map(f => ({ name: f.name, size: f.size })));

    setUploading(true);
    setUploadProgress(0);

    try {
      // 检查重复文档
      const filesToUpload: File[] = [];
      const duplicateFiles: string[] = [];

      for (let i = 0; i < files.length; i++) {
        const file = files[i];

        // 兼容不同的数据结构：Document vs KbDocument
        const isDuplicate = documents.some(doc => {
          // 获取文件名（兼容不同字段名）
          const docFilename = (doc as any).filename || (doc as any).filename;
          // 获取文件大小（兼容不同字段名）
          const docSize = (doc as any).size || (doc as any).metadata?.file_size;

          return docFilename === file.name && Number(docSize) === file.size;
        });

        console.log(`检查文件: ${file.name} (${file.size} bytes) - ${isDuplicate ? '重复' : '新文件'}`);

        if (isDuplicate) {
          duplicateFiles.push(file.name);
        } else {
          filesToUpload.push(file);
        }
      }

      // 如果有重复文件，显示警告
      if (duplicateFiles.length > 0) {
        const duplicateList = duplicateFiles.map(f => `• ${f}`).join('\n');
        const shouldContinue = window.confirm(
          `以下文档已存在，是否继续上传其他文档？\n\n${duplicateList}\n\n点击"确定"继续上传非重复文档，点击"取消"停止上传。`
        );
        if (!shouldContinue) {
          setUploading(false);
          setUploadProgress(0);
          return;
        }
      }

      // 如果没有文件需要上传，直接返回
      if (filesToUpload.length === 0) {
        alert('所选文档已全部存在，未上传任何文档！');
        setUploading(false);
        setUploadProgress(0);
        return;
      }

      // 上传非重复文档
      for (let i = 0; i < filesToUpload.length; i++) {
        const file = filesToUpload[i];
        await documentApi.uploadDocument(file, (progress) => {
          setUploadProgress(Math.round(((i + 1) / filesToUpload.length) * 100));
        });
      }

      // 刷新文档列表
      await loadDocuments();
      await loadKbStatus();

      setShowUploadModal(false);

      // 显示上传结果
      const uploadedCount = filesToUpload.length;
      const skippedCount = duplicateFiles.length;
      if (skippedCount > 0) {
        alert(`文档上传完成！\n成功: ${uploadedCount} 个\n跳过重复: ${skippedCount} 个`);
      } else {
        alert(`文档上传成功！共上传 ${uploadedCount} 个文档`);
      }
    } catch (error) {
      console.error('上传失败:', error);
      alert('上传失败，请重试');
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const handleDeleteDocuments = async () => {
    if (selectedDocs.size === 0) return;

    if (!window.confirm(`确定要删除选中的 ${selectedDocs.size} 个文档吗？`)) {
      return;
    }

    try {
      await documentApi.batchDeleteDocuments(Array.from(selectedDocs));
      setSelectedDocs(new Set());
      await loadDocuments();
      await loadKbStatus();
      alert('删除成功！');
    } catch (error) {
      console.error('删除失败:', error);
      alert('删除失败，请重试');
    }
  };

  const handleResetKb = async () => {
    if (!window.confirm('确定要重置知识库吗？这将清空所有文档和数据！')) {
      return;
    }

    try {
      await knowledgeBaseApi.resetVectorStore();
      setDocuments([]);
      await loadKbStatus();
      alert('知识库已重置！');
    } catch (error) {
      console.error('重置失败:', error);
      alert('重置失败，请重试');
    }
  };

  const loadKbDocuments = async () => {
    setLoadingDocList(true);
    try {
      const response = await knowledgeBaseApi.getDocuments();
      if (response.success && response.data) {
        setKbDocuments(response.data);
      }
    } catch (error) {
      console.error('加载文档列表失败:', error);
      alert('加载文档列表失败');
    } finally {
      setLoadingDocList(false);
    }
  };

  const handleOpenDocListModal = () => {
    setShowDocListModal(true);
    loadKbDocuments();
  };

  const handleDeleteKbDocument = async (docId: string, filename: string) => {
    if (!window.confirm(`确定要删除文档 "${filename}" 吗？此操作不可撤销！`)) {
      return;
    }

    try {
      await knowledgeBaseApi.deleteDocument(docId);
      // 重新加载文档列表和状态
      await loadKbDocuments();
      await loadKbStatus();
      alert('文档已删除！');
    } catch (error) {
      console.error('删除文档失败:', error);
      alert('删除文档失败，请重试');
    }
  };

  const formatIngestedAt = (dateStr: string) => {
    if (!dateStr) return '-';

    try {
      // 解析 ISO 时间字符串（带时区信息）
      const date = new Date(dateStr);

      // 检查是否是有效日期
      if (isNaN(date.getTime())) {
        return dateStr; // 返回原字符串
      }

      // 格式化显示时间（使用本地时区）
      const year = date.getFullYear();
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const day = String(date.getDate()).padStart(2, '0');
      const hours = String(date.getHours()).padStart(2, '0');
      const minutes = String(date.getMinutes()).padStart(2, '0');
      const seconds = String(date.getSeconds()).padStart(2, '0');

      return `${year}-${month}-${day} ${hours}:${minutes}`;
    } catch {
      return dateStr;
    }
  };

  const toggleDocSelection = (docId: string) => {
    const newSelection = new Set(selectedDocs);
    if (newSelection.has(docId)) {
      newSelection.delete(docId);
    } else {
      newSelection.add(docId);
    }
    setSelectedDocs(newSelection);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  if (!rightPanelOpen) {
    return null;
  }

  return (
    <>
      <div className="h-full flex flex-col bg-chat-bg border-l border-chat-border">
        {/* 顶部标题栏 */}
        <div className="p-4 border-b border-chat-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Settings className="text-chat-accent" size={20} />
              <h1 className="text-lg font-semibold text-chat-text">系统管理</h1>
            </div>
            <button
              onClick={() => setRightPanelOpen(false)}
              className="p-1 hover:bg-chat-bg rounded transition-colors"
              title="收起"
            >
              <ChevronRight className="text-chat-text" size={20} />
            </button>
          </div>
        </div>

        {/* 功能导航 */}
        <div className="p-4 border-b border-chat-border">
          <div className="space-y-2">
            <button
              onClick={() => setActiveSection(activeSection === 'documents' ? null : 'documents')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                activeSection === 'documents'
                  ? 'bg-chat-bg-secondary text-chat-text'
                  : 'text-gray-400 hover:bg-chat-bg-secondary hover:text-chat-text'
              }`}
            >
              <FileText size={20} />
              <span>文档管理</span>
            </button>

            <button
              onClick={() => setActiveSection(activeSection === 'knowledge' ? null : 'knowledge')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                activeSection === 'knowledge'
                  ? 'bg-chat-bg-secondary text-chat-text'
                  : 'text-gray-400 hover:bg-chat-bg-secondary hover:text-chat-text'
              }`}
            >
              <Database size={20} />
              <span>知识库管理</span>
            </button>
          </div>
        </div>

        {/* 内容区域 */}
        <div className="flex-1 overflow-y-auto p-4">
          {activeSection === 'documents' && (
            <div className="space-y-4">
              {/* 上传按钮 */}
              <div className="flex gap-2">
                <button
                  onClick={() => setShowUploadModal(true)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-chat-accent hover:bg-opacity-90 text-white rounded-lg transition-colors"
                >
                  <Upload size={16} />
                  <span>上传文档</span>
                </button>

                {selectedDocs.size > 0 && (
                  <button
                    onClick={handleDeleteDocuments}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                  >
                    <Trash2 size={16} className="inline mr-1" />
                    删除 ({selectedDocs.size})
                  </button>
                )}
              </div>

              {/* 文档列表 */}
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-gray-400">
                  已上传文档 ({documents.length})
                </h3>

                {documents.length === 0 ? (
                  <div className="text-center text-gray-400 py-8">
                    暂无文档
                  </div>
                ) : (
                  documents.map((doc) => (
                    <div
                      key={doc.id}
                      onClick={() => toggleDocSelection(doc.id)}
                      className={`p-3 rounded-lg cursor-pointer transition-colors border ${
                        selectedDocs.has(doc.id)
                          ? 'border-chat-accent bg-chat-bg-secondary'
                          : 'border-chat-border hover:border-chat-accent'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <input
                          type="checkbox"
                          checked={selectedDocs.has(doc.id)}
                          onChange={() => toggleDocSelection(doc.id)}
                          className="mt-1"
                          onClick={(e) => e.stopPropagation()}
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-chat-text truncate">
                            {doc.filename}
                          </p>
                          <p className="text-xs text-gray-400">
                            {formatFileSize(doc.size)} • {doc.type}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {activeSection === 'knowledge' && (
            <div className="space-y-4">
              {/* 知识库状态 */}
              {kbStatus && (
                <div className="p-4 bg-chat-bg-secondary rounded-lg border border-chat-border">
                  <h3 className="text-sm font-medium text-chat-text mb-3">
                    知识库状态
                  </h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">文档总数:</span>
                      <span className="text-chat-text">{kbStatus.totalDocuments || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">状态:</span>
                      <span className={`${
                        kbStatus.vectorStatus === 'healthy' ? 'text-green-400' : 'text-yellow-400'
                      }`}>
                        {kbStatus.vectorStatus === 'healthy' ? '正常' : '警告'}
                      </span>
                    </div>
                    <button
                      onClick={handleOpenDocListModal}
                      className="w-full mt-2 flex items-center justify-center gap-2 px-3 py-2 bg-chat-accent hover:bg-opacity-90 text-white rounded transition-colors text-sm"
                    >
                      <List size={14} />
                      <span>文档清单</span>
                    </button>
                  </div>
                </div>
              )}

              {/* 重置按钮 */}
              <button
                onClick={handleResetKb}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
              >
                <RefreshCw size={16} />
                <span>重置知识库</span>
              </button>

              <div className="p-4 bg-yellow-900/20 border border-yellow-600/30 rounded-lg">
                <p className="text-sm text-yellow-200">
                  ⚠️ 注意：重置知识库将清空所有已上传的文档和向量数据，此操作不可撤销！
                </p>
              </div>
            </div>
          )}

          {activeSection === null && (
            <div className="text-center text-gray-400 py-8">
              请选择一个管理功能
            </div>
          )}
        </div>
      </div>

      {/* 上传模态框 */}
      {showUploadModal && (
        <Modal
          isOpen={showUploadModal}
          onClose={() => setShowUploadModal(false)}
          title="上传文档"
        >
          <div className="space-y-4">
            <div className="border-2 border-dashed border-chat-border rounded-lg p-8 text-center">
              <Upload className="mx-auto text-gray-400 mb-4" size={48} />
              <p className="text-gray-400 mb-4">
                点击选择文件或拖拽文件到此处
              </p>
              <input
                type="file"
                multiple
                accept=".pdf,.docx,.xlsx,.xls"
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    handleFileUpload(e.target.files);
                  }
                }}
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                className="inline-block px-6 py-2 bg-chat-accent hover:bg-opacity-90 text-white rounded-lg cursor-pointer transition-colors"
              >
                选择文件
              </label>
            </div>

            {uploading && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm text-gray-400">
                  <span>上传中...</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="w-full bg-chat-bg rounded-full h-2">
                  <div
                    className="bg-chat-accent h-2 rounded-full transition-all"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            )}

            <div className="text-xs text-gray-400">
              支持的文件格式：PDF, DOCX, XLSX, XLS
            </div>
          </div>
        </Modal>
      )}

      {/* 文档清单模态框 */}
      {showDocListModal && (
        <Modal
          isOpen={showDocListModal}
          onClose={() => setShowDocListModal(false)}
          title="知识库文档清单"
        >
          <div className="space-y-4">
            {loadingDocList ? (
              <div className="text-center text-gray-400 py-8">
                加载中...
              </div>
            ) : kbDocuments.length === 0 ? (
              <div className="text-center text-gray-400 py-8">
                知识库暂无文档
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {kbDocuments.map((doc) => (
                  <div
                    key={doc.doc_id}
                    className="p-3 bg-chat-bg-secondary rounded-lg border border-chat-border"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-chat-text break-all">
                          {doc.filename}
                        </p>
                        <div className="flex items-center gap-1 mt-1 text-xs text-gray-400">
                          <Calendar size={12} />
                          <span>{formatIngestedAt(doc.ingested_at)}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDeleteKbDocument(doc.doc_id, doc.filename)}
                        className="flex-shrink-0 p-1 text-red-400 hover:text-red-300 hover:bg-red-900/20 rounded transition-colors"
                        title="删除文档"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Modal>
      )}
    </>
  );
};

export default RightSidebar;

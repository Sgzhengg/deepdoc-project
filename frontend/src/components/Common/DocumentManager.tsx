import React, { useState, useEffect } from 'react';
import {
  FileText,
  Search,
  Filter,
  Grid3x3,
  List,
  Download,
  Share,
  Eye,
  Calendar,
  FileType,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import type { Document } from '@/types';

interface DocumentManagerProps {
  documents: Document[];
  onRefresh: () => void;
  onView?: (document: Document) => void;
}

type ViewMode = 'grid' | 'list';
type SortBy = 'name' | 'date' | 'size' | 'type';
type FilterStatus = 'all' | 'completed' | 'processing' | 'failed';

const DocumentManager: React.FC<DocumentManagerProps> = ({
  documents,
  onRefresh,
  onView,
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [sortBy, setSortBy] = useState<SortBy>('date');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDocuments, setSelectedDocuments] = useState<Set<string>>(new Set());

  // 过滤和排序文档
  const filteredAndSortedDocuments = documents
    .filter((doc) => {
      // 状态过滤
      if (filterStatus !== 'all' && doc.status !== filterStatus) return false;

      // 搜索过滤
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        return (
          doc.filename.toLowerCase().includes(query) ||
          doc.type.toLowerCase().includes(query)
        );
      }

      return true;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.filename.localeCompare(b.filename);
        case 'date':
          return new Date(b.uploadTime).getTime() - new Date(a.uploadTime).getTime();
        case 'size':
          return b.size - a.size;
        case 'type':
          return a.type.localeCompare(b.type);
        default:
          return 0;
      }
    });

  const toggleSelectDocument = (docId: string) => {
    setSelectedDocuments((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(docId)) {
        newSet.delete(docId);
      } else {
        newSet.add(docId);
      }
      return newSet;
    });
  };

  const toggleSelectAll = () => {
    if (selectedDocuments.size === filteredAndSortedDocuments.length) {
      setSelectedDocuments(new Set());
    } else {
      setSelectedDocuments(new Set(filteredAndSortedDocuments.map((d) => d.id)));
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return '刚刚';
    if (diffMins < 60) return `${diffMins}分钟前`;
    if (diffHours < 24) return `${diffHours}小时前`;
    if (diffDays < 7) return `${diffDays}天前`;
    return date.toLocaleDateString('zh-CN');
  };

  const getStatusBadge = (status: Document['status']) => {
    const config = {
      completed: { label: '已入库', className: 'bg-green-500/20 text-green-400 border-green-500/50' },
      processing: { label: '处理中', className: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50' },
      failed: { label: '失败', className: 'bg-red-500/20 text-red-400 border-red-500/50' },
    };

    const { label, className } = config[status];
    return (
      <span className={`px-2 py-1 text-xs rounded border ${className}`}>
        {label}
      </span>
    );
  };

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') return '📄';
    if (['doc', 'docx'].includes(ext || '')) return '📝';
    if (['xls', 'xlsx'].includes(ext || '')) return '📊';
    if (['ppt', 'pptx'].includes(ext || '')) return '📽️';
    return '📄';
  };

  return (
    <div className="h-full flex flex-col bg-chat-bg overflow-hidden">
      {/* 工具栏 */}
      <div className="p-4 border-b border-chat-border space-y-4">
        {/* 搜索和筛选 */}
        <div className="flex items-center gap-3">
          <div className="flex-1 relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索文档..."
              className="w-full px-4 py-2 pl-10 bg-chat-input border border-chat-border rounded-lg text-chat-text placeholder-gray-500 focus:outline-none focus:border-chat-accent"
            />
            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
          </div>

          {/* 状态筛选 */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as FilterStatus)}
            className="px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text focus:outline-none focus:border-chat-accent"
          >
            <option value="all">全部状态</option>
            <option value="completed">已入库</option>
            <option value="processing">处理中</option>
            <option value="failed">失败</option>
          </select>

          {/* 排序 */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortBy)}
            className="px-3 py-2 bg-chat-input border border-chat-border rounded-lg text-chat-text focus:outline-none focus:border-chat-accent"
          >
            <option value="date">按日期</option>
            <option value="name">按名称</option>
            <option value="size">按大小</option>
            <option value="type">按类型</option>
          </select>

          {/* 视图切换 */}
          <div className="flex border border-chat-border rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 transition-colors ${
                viewMode === 'list'
                  ? 'bg-chat-accent text-white'
                  : 'bg-chat-input text-gray-400 hover:text-chat-text'
              }`}
              title="列表视图"
            >
              <List size={18} />
            </button>
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 transition-colors ${
                viewMode === 'grid'
                  ? 'bg-chat-accent text-white'
                  : 'bg-chat-input text-gray-400 hover:text-chat-text'
              }`}
              title="网格视图"
            >
              <Grid3x3 size={18} />
            </button>
          </div>

          {/* 刷新 */}
          <button
            onClick={onRefresh}
            className="p-2 bg-chat-input hover:bg-chat-bg-secondary border border-chat-border rounded-lg text-gray-400 hover:text-chat-text transition-colors"
            title="刷新"
          >
            <RefreshCw size={18} />
          </button>
        </div>

        {/* 批量操作 */}
        {selectedDocuments.size > 0 && (
          <div className="flex items-center justify-between p-3 bg-chat-accent/10 border border-chat-accent/30 rounded-lg">
            <span className="text-sm text-chat-text">
              已选择 {selectedDocuments.size} 个文档
            </span>
            <div className="flex items-center gap-2">
              <button className="flex items-center gap-2 px-3 py-1.5 bg-chat-accent hover:bg-chat-accent/90 text-white rounded-lg text-sm transition-colors">
                <Download size={16} />
                <span>下载</span>
              </button>
              <button className="flex items-center gap-2 px-3 py-1.5 bg-chat-input hover:bg-chat-bg-secondary text-chat-text rounded-lg text-sm border border-chat-border transition-colors">
                <Share size={16} />
                <span>分享</span>
              </button>
              <button className="flex items-center gap-2 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm transition-colors">
                <Trash2 size={16} />
                <span>删除</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 文档列表 */}
      <div className="flex-1 overflow-y-auto p-4">
        {filteredAndSortedDocuments.length === 0 ? (
          <div className="text-center text-gray-400 py-12">
            <FileText size={48} className="mx-auto mb-4 text-gray-500" />
            <p className="text-sm">
              {searchQuery || filterStatus !== 'all'
                ? '没有找到匹配的文档'
                : '暂无文档'}
            </p>
          </div>
        ) : viewMode === 'list' ? (
          <div className="space-y-2">
            {/* 表头 */}
            <div className="flex items-center gap-3 px-4 py-2 bg-chat-bg-secondary rounded-t-lg border border-chat-border">
              <input
                type="checkbox"
                checked={selectedDocuments.size === filteredAndSortedDocuments.length}
                onChange={toggleSelectAll}
                className="w-4 h-4"
              />
              <span className="text-xs text-gray-400 w-8"></span>
              <span className="text-xs text-gray-400 flex-1">文件名</span>
              <span className="text-xs text-gray-400 w-24">状态</span>
              <span className="text-xs text-gray-400 w-24">大小</span>
              <span className="text-xs text-gray-400 w-32">上传时间</span>
              <span className="text-xs text-gray-400 w-20">操作</span>
            </div>

            {/* 列表项 */}
            {filteredAndSortedDocuments.map((doc) => (
              <div
                key={doc.id}
                className={`flex items-center gap-3 px-4 py-3 bg-chat-bg-secondary border border-chat-border rounded-lg hover:border-chat-accent transition-colors ${
                  selectedDocuments.has(doc.id) ? 'ring-2 ring-chat-accent' : ''
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedDocuments.has(doc.id)}
                  onChange={() => toggleSelectDocument(doc.id)}
                  className="w-4 h-4"
                />
                <span className="text-lg">{getFileIcon(doc.filename)}</span>
                <span className="flex-1 text-sm text-gray-200 truncate">
                  {doc.filename}
                </span>
                {getStatusBadge(doc.status)}
                <span className="text-xs text-gray-400 w-24">
                  {formatFileSize(doc.size)}
                </span>
                <span className="text-xs text-gray-400 w-32 flex items-center gap-1">
                  <Calendar size={12} />
                  {formatDate(doc.uploadTime)}
                </span>
                <div className="flex items-center gap-1 w-20">
                  {onView && (
                    <button
                      onClick={() => onView(doc)}
                      className="p-1.5 hover:bg-chat-bg rounded transition-colors"
                      title="查看"
                    >
                      <Eye size={14} className="text-gray-400" />
                    </button>
                  )}
                  <button
                    className="p-1.5 hover:bg-chat-bg rounded transition-colors"
                    title="下载"
                  >
                    <Download size={14} className="text-gray-400" />
                  </button>
                  <button
                    className="p-1.5 hover:bg-chat-bg rounded transition-colors"
                    title="删除"
                  >
                    <Trash2 size={14} className="text-red-400" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          // 网格视图
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {filteredAndSortedDocuments.map((doc) => (
              <div
                key={doc.id}
                className={`p-4 bg-chat-bg-secondary border border-chat-border rounded-lg hover:border-chat-accent transition-colors cursor-pointer ${
                  selectedDocuments.has(doc.id) ? 'ring-2 ring-chat-accent' : ''
                }`}
                onClick={() => toggleSelectDocument(doc.id)}
              >
                <div className="flex items-start justify-between mb-3">
                  <span className="text-4xl">{getFileIcon(doc.filename)}</span>
                  <input
                    type="checkbox"
                    checked={selectedDocuments.has(doc.id)}
                    onChange={(e) => {
                      e.stopPropagation();
                      toggleSelectDocument(doc.id);
                    }}
                    className="w-4 h-4"
                  />
                </div>

                <h4 className="text-sm font-medium text-gray-200 truncate mb-2">
                  {doc.filename}
                </h4>

                <div className="flex items-center gap-2 mb-2">
                  {getStatusBadge(doc.status)}
                </div>

                <div className="text-xs text-gray-400 space-y-1">
                  <div className="flex items-center gap-1">
                    <FileType size={12} />
                    <span>{doc.type}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Calendar size={12} />
                    <span>{formatDate(doc.uploadTime)}</span>
                  </div>
                  <div>{formatFileSize(doc.size)}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentManager;

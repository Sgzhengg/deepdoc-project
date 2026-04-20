import React, { useEffect, useState } from 'react';
import {
  Plus,
  Trash2,
  MessageSquare,
  CheckSquare,
  Square,
  X,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { chatApi } from '@/services/api';

const LeftSidebar: React.FC = () => {
  const {
    conversations,
    setConversations,
    currentConversationId,
    setCurrentConversation,
    startNewConversation,
    deleteConversation,
    selectedConversationIds,
    toggleConversationSelection,
    clearConversationSelection,
    selectAllConversations,
    batchDeleteConversations,
  } = useStore();

  const [loading, setLoading] = useState(false);
  const [batchMode, setBatchMode] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = async () => {
    setLoading(true);
    try {
      const response = await chatApi.getConversations();
      if (response.success && response.data) {
        setConversations(response.data);
      }
    } catch (error) {
      // 会话历史功能可能未实现，静默处理
      console.log('会话历史功能暂未实现');
      setConversations([]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewConversation = () => {
    startNewConversation();
    exitBatchMode();
  };

  const handleDeleteConversation = async (conversationId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('确定要删除这个对话吗？')) {
      try {
        await chatApi.deleteConversation(conversationId);
        // 更新本地状态
        deleteConversation(conversationId);
        // 为了避免状态不一致，直接重新加载最新的会话列表
        await loadConversations();
      } catch (error) {
        console.error('删除对话失败:', error);
        alert('删除失败，请重试');
      }
    }
  };

  const enterBatchMode = () => {
    setBatchMode(true);
    clearConversationSelection();
  };

  const exitBatchMode = () => {
    setBatchMode(false);
    clearConversationSelection();
  };

  const toggleSelectAll = () => {
    if (selectedConversationIds.length === conversations.length) {
      clearConversationSelection();
    } else {
      selectAllConversations();
    }
  };

  const handleBatchDelete = async () => {
    if (selectedConversationIds.length === 0) {
      return;
    }

    if (window.confirm(`确定要删除选中的 ${selectedConversationIds.length} 个对话吗？`)) {
      setDeleting(true);
      try {
        const response = await chatApi.batchDeleteConversations(selectedConversationIds);
        if (response.success) {
          batchDeleteConversations(selectedConversationIds);
          // 重新加载会话列表
          await loadConversations();
          alert(`成功删除 ${response.deleted_count} 个对话`);
        } else {
          alert('批量删除失败，请重试');
        }
      } catch (error) {
        console.error('批量删除对话失败:', error);
        alert('批量删除失败，请重试');
      } finally {
        setDeleting(false);
        exitBatchMode();
      }
    }
  };

  const handleItemClick = (conversationId: string) => {
    if (batchMode) {
      toggleConversationSelection(conversationId);
    } else {
      setCurrentConversation(conversationId);
    }
  };

  const formatPreview = (text: string, maxLength = 30) => {
    if (!text || text === undefined || text === null) return '暂无预览';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
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

  const allSelected = conversations.length > 0 && selectedConversationIds.length === conversations.length;

  return (
    <div className="h-full flex flex-col bg-chat-bg">
      {/* 顶部标题 */}
      <div className="p-4 border-b border-chat-border">
        <div className="flex items-center gap-2">
          <MessageSquare className="text-chat-accent" size={24} />
          <h1 className="text-lg font-semibold text-chat-text">
            渠道业务AI助手
          </h1>
        </div>
      </div>

      {/* 会话历史列表 */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-2">
          {/* 历史对话标题栏 */}
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-gray-400">历史对话</h2>

            {/* 批量操作按钮 */}
            {conversations.length > 0 && (
              <div className="flex items-center gap-2">
                {batchMode ? (
                  <>
                    {/* 全选/取消全选 */}
                    <button
                      onClick={toggleSelectAll}
                      className="p-1 hover:bg-chat-bg rounded transition-all"
                      title={allSelected ? '取消全选' : '全选'}
                    >
                      {allSelected ? (
                        <CheckSquare size={16} className="text-chat-accent" />
                      ) : (
                        <Square size={16} className="text-gray-400" />
                      )}
                    </button>

                    {/* 已选择数量 */}
                    {selectedConversationIds.length > 0 && (
                      <span className="text-xs text-chat-accent">
                        {selectedConversationIds.length} 已选
                      </span>
                    )}

                    {/* 批量删除按钮 */}
                    {selectedConversationIds.length > 0 && (
                      <button
                        onClick={handleBatchDelete}
                        disabled={deleting}
                        className="flex items-center gap-1 px-2 py-1 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded transition-all disabled:opacity-50"
                        title="删除选中"
                      >
                        <Trash2 size={14} />
                        <span className="text-xs">
                          {deleting ? '删除中...' : '删除'}
                        </span>
                      </button>
                    )}

                    {/* 退出批量模式 */}
                    <button
                      onClick={exitBatchMode}
                      className="p-1 hover:bg-chat-bg rounded transition-all"
                      title="退出批量选择"
                    >
                      <X size={16} className="text-gray-400" />
                    </button>
                  </>
                ) : (
                  /* 进入批量模式按钮 */
                  <button
                    onClick={enterBatchMode}
                    className="flex items-center gap-1 px-2 py-1 hover:bg-chat-bg text-gray-400 hover:text-chat-text rounded transition-all text-xs"
                    title="批量管理"
                  >
                    <CheckSquare size={14} />
                    <span>管理</span>
                  </button>
                )}
              </div>
            )}
          </div>

          {loading ? (
            <div className="text-center text-gray-400 py-8">加载中...</div>
          ) : conversations.length === 0 ? (
            <div className="text-center text-gray-400 py-8">暂无历史对话</div>
          ) : (
            conversations.map((conversation) => {
              const isSelected = selectedConversationIds.includes(conversation.id);
              const isActive = currentConversationId === conversation.id;

              return (
                <div
                  key={conversation.id}
                  onClick={() => handleItemClick(conversation.id)}
                  className={`group relative p-3 rounded-lg cursor-pointer transition-colors ${
                    isActive && !batchMode
                      ? 'bg-chat-bg-secondary text-chat-text'
                      : 'hover:bg-chat-bg-secondary text-gray-300 hover:text-chat-text'
                  } ${isSelected ? 'ring-1 ring-chat-accent' : ''}`}
                >
                  <div className="flex items-start gap-2">
                    {/* 批量选择复选框 */}
                    {batchMode && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleConversationSelection(conversation.id);
                        }}
                        className="mt-1 p-0.5 hover:bg-chat-bg rounded transition-all flex-shrink-0"
                      >
                        {isSelected ? (
                          <CheckSquare size={16} className="text-chat-accent" />
                        ) : (
                          <Square size={16} className="text-gray-400" />
                        )}
                      </button>
                    )}

                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-sm truncate mb-1">
                        {conversation.title}
                      </h3>
                      <p className="text-xs text-gray-400 mb-1">
                        {formatTime(conversation.timestamp)}
                      </p>
                      <p className="text-xs text-gray-500 truncate">
                        {formatPreview(conversation.preview)}
                      </p>
                    </div>

                    {/* 单个删除按钮（非批量模式时显示） */}
                    {!batchMode && (
                      <button
                        onClick={(e) => handleDeleteConversation(conversation.id, e)}
                        className="p-1 hover:bg-chat-bg rounded transition-all flex-shrink-0"
                        title="删除对话"
                      >
                        <Trash2 size={14} className="text-red-400" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* 底部新建对话按钮 */}
      <div className="p-4 border-t border-chat-border">
        <button
          onClick={handleNewConversation}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-chat-input hover:bg-chat-bg-secondary text-chat-text rounded-lg border border-chat-border transition-colors"
        >
          <Plus size={20} />
          <span>新建对话</span>
        </button>
      </div>
    </div>
  );
};

export default LeftSidebar;

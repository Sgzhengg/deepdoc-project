import React, { useEffect, useState } from 'react';
import { Trash2, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { LocalConversation } from '@/utils/mobileStorage';
import {
  getLocalConversations,
  deleteLocalConversation,
} from '@/utils/mobileStorage';
import './MobileHistory.css';

const MobileHistory: React.FC = () => {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<LocalConversation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadConversations();
  }, []);

  const loadConversations = () => {
    setLoading(true);
    // 从 localStorage 加载对话
    const localConversations = getLocalConversations();
    setConversations(localConversations);
    setLoading(false);
  };

  const handleBackToChat = () => {
    navigate('/');
  };

  const handleSelectConversation = (conversationId: string) => {
    navigate(`/?id=${conversationId}`);
  };

  const handleDelete = async (conversationId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('确定要删除这个对话吗？')) {
      deleteLocalConversation(conversationId);
      setConversations(conversations.filter((c) => c.id !== conversationId));
    }
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

  return (
    <div className="mobile-history">
      {/* 顶部导航栏 */}
      <div className="history-header">
        <button className="back-btn" onClick={handleBackToChat}>
          <ArrowLeft size={20} />
        </button>
        <h1 className="history-title">历史对话</h1>
        <div className="header-spacer"></div>
      </div>

      {/* 对话列表 */}
      <div className="history-list">
        {loading ? (
          <div className="loading-state">加载中...</div>
        ) : conversations.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📝</div>
            <p className="empty-text">暂无历史对话</p>
            <button className="empty-action" onClick={handleBackToChat}>
              开始对话
            </button>
          </div>
        ) : (
          conversations.map((conversation) => (
            <div
              key={conversation.id}
              className="history-item"
              onClick={() => handleSelectConversation(conversation.id)}
            >
              <div className="history-item-content">
                <h3 className="history-item-title">{conversation.title}</h3>
                <p className="history-item-preview">{conversation.preview}</p>
                <span className="history-item-time">
                  {formatTime(conversation.timestamp)} · {conversation.messageCount} 条消息
                </span>
              </div>
              <button
                className="history-item-delete"
                onClick={(e) => handleDelete(conversation.id, e)}
                aria-label="删除对话"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default MobileHistory;

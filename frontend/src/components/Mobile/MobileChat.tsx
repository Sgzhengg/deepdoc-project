import React, { useState, useRef, useEffect } from 'react';
import { Send, Plus } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { chatApi } from '@/services/api';
import type { Message } from '@/types';
import {
  getLocalConversations,
  getLocalConversation,
  createLocalConversation,
  addMessageToConversation,
  updateConversationMessages,
} from '@/utils/mobileStorage';
import './MobileChat.css';

interface LocalMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: any[];
  relevanceScore?: number;
  reasoning?: string[];
}

const MobileChat: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const conversationId = searchParams.get('id');

  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [isLoading, setLoading] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(conversationId);

  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 加载对话消息
  useEffect(() => {
    if (currentConversationId) {
      const conversation = getLocalConversation(currentConversationId);
      if (conversation) {
        setMessages(conversation.messages);
      } else {
        setMessages([]);
      }
    } else {
      setMessages([]);
    }
  }, [currentConversationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleNewChat = () => {
    setMessages([]);
    setCurrentConversationId(null);
    navigate('/');
  };

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const messageContent = inputValue.trim();
    setInputValue('');
    setLoading(true);

    // 创建用户消息
    const userMessage: LocalMessage = {
      id: `msg_${Date.now()}_user`,
      role: 'user',
      content: messageContent,
      timestamp: new Date().toISOString(),
    };

    // 添加到界面
    setMessages((prev) => [...prev, userMessage]);

    // 如果是新对话，创建本地会话
    let conversationId = currentConversationId;
    if (!conversationId) {
      const newConversation = createLocalConversation(messageContent);
      conversationId = newConversation.id;
      setCurrentConversationId(conversationId);
      // 更新 URL
      navigate(`/?id=${conversationId}`, { replace: true });
    } else {
      // 添加用户消息到本地存储
      addMessageToConversation(conversationId, userMessage);
    }

    try {
      // 调用 API 获取 AI 回复
      const response = await chatApi.sendMessage({
        message: messageContent,
        // 不发送 session_id，每次都是新请求
      });

      if (response && (response.success || response.answer)) {
        const assistantMessage: LocalMessage = {
          id: `msg_${Date.now()}_assistant`,
          role: 'assistant',
          content: response.answer || response.content || '',
          timestamp: new Date().toISOString(),
          sources: response.sources || [],
          relevanceScore: response.confidence || 0,
          reasoning: response.reasoning || [],
        };

        // 更新界面
        setMessages((prev) => [...prev, assistantMessage]);

        // 保存到本地存储
        addMessageToConversation(conversationId!, assistantMessage);
      }
    } catch (error) {
      console.error('聊天错误:', error);
      const errorMessage: LocalMessage = {
        id: `msg_${Date.now()}_error`,
        role: 'assistant',
        content: '抱歉，我遇到了一些问题。请稍后再试。',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      addMessageToConversation(conversationId!, errorMessage);
    } finally {
      setLoading(false);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="mobile-chat">
      {/* 顶部工具栏 */}
      <div className="chat-toolbar">
        <button className="new-chat-btn" onClick={handleNewChat}>
          <Plus size={18} />
          <span>新建对话</span>
        </button>
      </div>

      {/* 消息展示区 */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <div className="welcome-icon">💬</div>
            <h2 className="welcome-title">渠道业务AI助手</h2>
            <p className="welcome-desc">我可以帮您查询渠道业务相关问题</p>
            <div className="welcome-examples">
              <p className="example-title">您可以问我：</p>
              <p className="example-item">• "29元套餐包含多少定向流量？"</p>
              <p className="example-item">• "服务补贴怎么计算？"</p>
              <p className="example-item">• "新业务有什么优惠？"</p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`message-row ${message.role === 'user' ? 'user' : 'assistant'}`}
            >
              <div className={`message-bubble ${message.role}`}>
                {message.role === 'assistant' && (
                  <div className="bubble-label">AI助手</div>
                )}
                <div className="bubble-content">{message.content}</div>

                {/* AI消息的额外信息 */}
                {message.role === 'assistant' && (
                  <div className="bubble-footer">
                    {/* 时间戳 */}
                    <div className="bubble-time">{formatTimestamp(message.timestamp)}</div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {/* 加载动画 */}
        {isLoading && (
          <div className="message-row assistant">
            <div className="message-bubble assistant">
              <div className="bubble-label">AI助手</div>
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 输入区域 */}
      <div className="chat-input-area">
        <div className="input-container">
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="请输入您的问题..."
            className="chat-input"
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
            className="send-btn"
          >
            <Send size={20} />
          </button>
        </div>
        <div className="input-hint">Enter 发送，Shift+Enter 换行</div>
      </div>
    </div>
  );
};

export default MobileChat;

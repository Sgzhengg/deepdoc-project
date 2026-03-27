import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip } from 'lucide-react';
import { useStore } from '@/store/useStore';
import { chatApi } from '@/services/api';
import type { Message } from '@/types';

const ChatArea: React.FC = () => {
  const {
    messages,
    setMessages,
    addMessage,
    isLoading,
    setLoading,
    setRightPanelOpen,
    setLeftSidebarOpen,
    leftSidebarOpen,
    currentConversationId,
    setCurrentConversation,
    addOrUpdateConversation,
  } = useStore();

  const [inputValue, setInputValue] = useState('');
  const [expandedReasoning, setExpandedReasoning] = useState<Set<string>>(new Set());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [loadingConversation, setLoadingConversation] = useState(false);

  // 监听当前会话 ID 变化，加载历史消息
  useEffect(() => {
    const loadConversationMessages = async () => {
      if (currentConversationId) {
        setLoadingConversation(true);
        try {
          const response = await chatApi.getConversationMessages(currentConversationId);
          if (response.success && response.data && response.data.messages) {
            setMessages(response.data.messages);
          }
        } catch (error) {
          console.error('加载历史消息失败:', error);
        } finally {
          setLoadingConversation(false);
        }
      } else {
        // 没有选中的会话，清空消息
        setMessages([]);
      }
    };

    loadConversationMessages();
  }, [currentConversationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date().toISOString(),
    };

    addMessage(userMessage);
    const messageToSend = inputValue.trim();
    setInputValue('');
    setLoading(true);

    try {
      console.log('发送消息:', messageToSend);
      const response = await chatApi.sendMessage({
        message: messageToSend,
        session_id: currentConversationId || undefined,
      });

      console.log('收到响应:', response);

      if (response && (response.success || response.answer)) {
        console.log('创建助手消息');
        const assistantMessage: Message = {
          id: Date.now().toString(),
          role: 'assistant',
          content: response.answer || response.content || '',
          timestamp: new Date().toISOString(),
          sources: response.sources || [],
          relevanceScore: response.confidence || 0,
          reasoning: response.reasoning || [],
        };
        console.log('助手消息:', assistantMessage);
        addMessage(assistantMessage);
        console.log('消息已添加');

        // 更新会话列表（如果返回了 session_id）
        if (response.session_id && response.session_id !== currentConversationId) {
          setCurrentConversation(response.session_id);

          // 创建或更新会话
          const allMessages = [...messages, userMessage, assistantMessage];
          const conversation = {
            id: response.session_id,
            title: messageToSend.substring(0, 30) + (messageToSend.length > 30 ? '...' : ''),
            preview: messageToSend.substring(0, 100) + (messageToSend.length > 100 ? '...' : ''),
            timestamp: new Date().toISOString(),
            messageCount: allMessages.length,
          };
          addOrUpdateConversation(conversation);
        }
      } else {
        console.error('无效响应格式:', response);
        throw new Error('无效的响应格式');
      }
    } catch (error) {
      console.error('聊天错误:', error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: 'assistant',
        content: '抱歉，我遇到了一些问题。请稍后再试。',
        timestamp: new Date().toISOString(),
      };
      addMessage(errorMessage);
    } finally {
      setLoading(false);
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  };

  const toggleReasoning = (messageId: string) => {
    setExpandedReasoning((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(messageId)) {
        newSet.delete(messageId);
      } else {
        newSet.add(messageId);
      }
      return newSet;
    });
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  /**
   * 解析并格式化答案为统一模板
   * 支持三种格式：
   * 1. 三段式：【直接回答】【详细说明】【数据来源】
   * 2. 两段式：【回答】【数据来源】
   * 3. 混合式：【直接回答】+ 直接内容 + 【数据来源】
   */
  const parseAnswerFormat = (content: string) => {
    const sections = {
      directAnswer: '',
      detail: '',
      sources: '',
      hasFormat: false
    };

    // 检查是否包含标准格式标记
    const hasDirectAnswer = content.includes('【直接回答】');
    const hasAnswer = content.includes('【回答】');
    const hasDetail = content.includes('【详细说明】');
    const hasSources = content.includes('【数据来源】');

    if (hasDirectAnswer || hasAnswer || hasDetail || hasSources) {
      sections.hasFormat = true;

      // 优先处理两段式格式：【回答】【数据来源】
      if (hasAnswer && !hasDirectAnswer) {
        const parts = content.split('【回答】');
        if (parts.length > 1) {
          let afterAnswer = parts[1];

          // 分割数据来源
          if (hasSources) {
            const sourcesParts = afterAnswer.split('【数据来源】');
            sections.directAnswer = sourcesParts[0].trim();
            sections.sources = sourcesParts[1] ? sourcesParts[1].trim() : '';
          } else {
            sections.directAnswer = afterAnswer.trim();
          }
        }
      }
      // 处理三段式格式：【直接回答】【详细说明】【数据来源】
      else if (hasDirectAnswer) {
        const parts = content.split('【直接回答】');
        if (parts.length > 1) {
          let afterDirect = parts[1];

          // 分割详细说明部分
          if (hasDetail) {
            const detailParts = afterDirect.split('【详细说明】');
            sections.directAnswer = detailParts[0].trim();
            afterDirect = detailParts[1] || '';
          } else {
            // 没有【详细说明】，则【直接回答】后面的所有内容（直到【数据来源】）都是详细内容
            if (hasSources) {
              const sourcesParts = afterDirect.split('【数据来源】');
              sections.directAnswer = sourcesParts[0].trim();
              sections.sources = sourcesParts[1] ? sourcesParts[1].trim() : '';
            } else {
              sections.directAnswer = afterDirect.trim();
            }
            afterDirect = '';
          }

          // 分割数据来源部分
          if (hasSources && afterDirect) {
            const sourcesParts = afterDirect.split('【数据来源】');
            sections.detail = sourcesParts[0].trim();
            sections.sources = sourcesParts[1] ? sourcesParts[1].trim() : '';
          } else if (hasDetail && afterDirect) {
            sections.detail = afterDirect.trim();
          }
        }
      } else if (hasDetail) {
        const parts = content.split('【详细说明】');
        if (parts.length > 1) {
          sections.detail = parts[1].trim();
          if (hasSources) {
            const sourcesParts = sections.detail.split('【数据来源】');
            sections.detail = sourcesParts[0].trim();
            sections.sources = sourcesParts[1] ? sourcesParts[1].trim() : '';
          }
        }
      } else if (hasSources) {
        const parts = content.split('【数据来源】');
        if (parts.length > 1) {
          sections.sources = parts[1].trim();
        }
      }
    }

    return sections;
  };

  /**
   * 渲染格式化的答案
   */
  const renderFormattedAnswer = (content: string) => {
    const sections = parseAnswerFormat(content);

    if (!sections.hasFormat) {
      // 没有标准格式，按原样显示
      return renderContent(content);
    }

    // 判断是两段式还是三段式
    const isTwoPartFormat = content.includes('【回答】') && !content.includes('【直接回答】');
    const titleText = isTwoPartFormat ? '【回答】' : '【直接回答】';

    return (
      <div className="space-y-4">
        {/* 【直接回答】或【回答】 */}
        {sections.directAnswer && (
          <div>
            <div className="text-sm font-semibold text-chat-accent mb-2">{titleText}</div>
            <div className="text-chat-text pl-4">
              {renderContent(sections.directAnswer)}
            </div>
          </div>
        )}

        {/* 【详细说明】（仅在三段式格式中显示） */}
        {sections.detail && !isTwoPartFormat && (
          <div>
            <div className="text-sm font-semibold text-chat-accent mb-2">【详细说明】</div>
            <div className="text-chat-text pl-4">
              {renderContent(sections.detail)}
            </div>
          </div>
        )}

        {/* 【数据来源】 */}
        {sections.sources && (
          <div>
            <div className="text-sm font-semibold text-chat-accent mb-2">【数据来源】</div>
            <div className="text-chat-text pl-4 text-sm text-gray-400">
              {renderContent(sections.sources)}
            </div>
          </div>
        )}
      </div>
    );
  };

  // 简单的代码块渲染（不使用 react-syntax-highlighter）
  const renderContent = (content: string) => {
    // 简单处理代码块
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = codeBlockRegex.exec(content)) !== null) {
      // 添加代码块前的文本
      if (match.index > lastIndex) {
        parts.push({
          type: 'text',
          content: content.slice(lastIndex, match.index),
        });
      }

      // 添加代码块
      parts.push({
        type: 'code',
        language: match[1] || 'text',
        content: match[2],
      });

      lastIndex = match.index + match[0].length;
    }

    // 添加剩余文本
    if (lastIndex < content.length) {
      parts.push({
        type: 'text',
        content: content.slice(lastIndex),
      });
    }

    if (parts.length === 0) {
      return <p className="whitespace-pre-wrap">{content}</p>;
    }

    return parts.map((part, index) => {
      if (part.type === 'code') {
        return (
          <pre key={index} className="bg-chat-bg p-3 rounded-lg overflow-x-auto my-2 border border-chat-border">
            <code className="text-sm text-gray-300">{part.content}</code>
          </pre>
        );
      }
      return (
        <p key={index} className="whitespace-pre-wrap mb-2">
          {part.content}
        </p>
      );
    });
  };

  return (
    <div className="h-full flex flex-col bg-chat-bg">
      {/* 消息展示区 */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {loadingConversation ? (
            <div className="text-center py-20">
              <div className="text-gray-400">加载历史对话中...</div>
            </div>
          ) : messages.length === 0 ? (
            <div className="text-center py-20">
              <div className="text-6xl mb-6">💬</div>
              <h2 className="text-2xl font-semibold text-chat-text mb-3">
                您好！我是运营商渠道业务AI助手
              </h2>
              <p className="text-gray-400 mb-6">
                我可以帮助您查询和分析运营商渠道业务相关的信息
              </p>
              <p className="text-sm text-gray-500">
                在下方输入框中输入您的问题，例如：
              </p>
              <div className="mt-4 text-sm text-gray-400 space-y-1">
                <p>• "29元潮玩青春卡套餐包含多少定向流量？"</p>
                <p>• "有哪些酬金政策？"</p>
                <p>• "办理新业务有什么优惠？"</p>
              </div>
            </div>
          ) : (
            messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`rounded-lg px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-chat-user-bubble text-chat-text max-w-[50%]'
                      : 'bg-chat-ai-bubble text-chat-text max-w-[95%]'
                  }`}
                >
                  {/* 消息内容 */}
                  <div className="prose prose-invert max-w-none">
                    {renderFormattedAnswer(message.content)}
                  </div>

                  {/* AI消息的额外信息 */}
                  {message.role === 'assistant' && (
                    <div className="mt-4 pt-4 border-t border-chat-border">
                      {/* 推理过程 */}
                      {message.reasoning && message.reasoning.length > 0 && (
                        <div>
                          <button
                            onClick={() => toggleReasoning(message.id)}
                            className="flex items-center gap-2 text-xs text-chat-accent hover:underline"
                          >
                            <span>🧠 推理过程</span>
                            <span>{expandedReasoning.has(message.id) ? '▼' : '▶'}</span>
                          </button>
                          {expandedReasoning.has(message.id) && (
                            <div className="mt-2 p-2 bg-chat-bg rounded border border-chat-border text-xs text-gray-400">
                              <ul className="list-disc list-inside space-y-1">
                                {message.reasoning.map((step, index) => (
                                  <li key={index}>{step}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}

                      {/* 时间戳 */}
                      <div className="mt-2 text-xs text-gray-500">
                        {formatTimestamp(message.timestamp)}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}

          {/* 加载动画 */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-chat-ai-bubble rounded-lg px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-chat-accent rounded-full animate-bounce" />
                  <div
                    className="w-2 h-2 bg-chat-accent rounded-full animate-bounce"
                    style={{ animationDelay: '0.1s' }}
                  />
                  <div
                    className="w-2 h-2 bg-chat-accent rounded-full animate-bounce"
                    style={{ animationDelay: '0.2s' }}
                  />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 输入区域 */}
      <div className="border-t border-chat-border p-4">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end gap-3 bg-chat-input rounded-lg border border-chat-border p-3">
            <button
              className="p-2 hover:bg-chat-bg-secondary rounded transition-colors flex-shrink-0"
              title="上传附件"
            >
              <Paperclip size={20} className="text-gray-400" />
            </button>
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="请输入您的问题... (Ctrl+Enter 发送)"
              className="flex-1 bg-transparent border-0 outline-none resize-none text-chat-text placeholder-gray-500 max-h-48 min-h-[24px]"
              rows={1}
              disabled={isLoading}
            />
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || isLoading}
              className="p-2 bg-chat-accent hover:bg-chat-accent/90 disabled:opacity-50 disabled:cursor-not-allowed rounded transition-colors flex-shrink-0"
              title="发送 (Ctrl+Enter)"
            >
              <Send size={20} className="text-white" />
            </button>
          </div>
          <div className="mt-2 text-xs text-gray-500 text-center">
            AI回答基于知识库内容，建议使用专业术语提问以获得更准确的答案
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatArea;

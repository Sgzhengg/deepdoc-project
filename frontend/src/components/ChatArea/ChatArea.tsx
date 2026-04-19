import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, X, FileText, Image, FileSpreadsheet } from 'lucide-react';
import { useStore } from '@/store/useStore';
import { chatApi, attachmentApi } from '@/services/api';
import type { Message } from '@/types';

interface Attachment {
  attachment_id: string;
  filename: string;
  file_type: string;
  file_size: number;
}

// 根据文件类型获取图标
const getFileIcon = (fileType: string) => {
  if (fileType.includes('pdf')) return <FileText className="text-red-500" />;
  if (fileType.includes('image')) return <Image className="text-blue-500" />;
  if (fileType.includes('sheet') || fileType.includes('excel')) return <FileSpreadsheet className="text-green-500" />;
  if (fileType.includes('word') || fileType.includes('document')) return <FileText className="text-blue-600" />;
  return <Paperclip className="text-gray-400" />;
};

// 格式化文件大小
const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
};

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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [attachments, setAttachments] = useState<Attachment[]>([]);

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

    // 准备附件ID列表
    const attachmentIds = attachments.map(att => att.attachment_id);

    try {
      console.log('发送消息:', messageToSend);
      console.log('附件列表:', attachmentIds);

      const response = await chatApi.sendMessage({
        message: messageToSend,
        session_id: currentConversationId || undefined,
        attachment_ids: attachmentIds.length > 0 ? attachmentIds : undefined,
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

        // 清空附件列表（消息发送后）
        setAttachments([]);

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

  const handleFileUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // 检查文件类型
    const allowedTypes = [
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/plain',
      'image/jpeg',
      'image/png'
    ];

    if (!allowedTypes.includes(file.type)) {
      alert('仅支持上传 PDF、Word (DOCX)、Excel (XLSX)、文本和图片文件');
      return;
    }

    // 检查文件大小 (10MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      alert('文件大小不能超过 10MB');
      return;
    }

    setUploadingFile(true);
    try {
      // 使用新的附件API
      const sessionId = currentConversationId || 'temp_session';
      const response = await attachmentApi.upload(file, sessionId);

      if (response.success && response.data) {
        // 添加到附件列表
        const newAttachment: Attachment = {
          attachment_id: response.data.attachment_id,
          filename: response.data.filename,
          file_type: response.data.file_type,
          file_size: response.data.file_size
        };
        setAttachments([...attachments, newAttachment]);
      } else {
        throw new Error(response.error || '上传失败');
      }
    } catch (error) {
      console.error('文件上传失败:', error);
      alert(`文件上传失败：${error instanceof Error ? error.message : '未知错误'}`);
    } finally {
      setUploadingFile(false);
      // 清空文件选择
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleRemoveAttachment = async (attachmentId: string) => {
    try {
      const sessionId = currentConversationId || 'temp_session';
      await attachmentApi.delete(attachmentId, sessionId);
      setAttachments(attachments.filter(att => att.attachment_id !== attachmentId));
    } catch (error) {
      console.error('删除附件失败:', error);
      alert('删除附件失败');
    }
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
  const renderFormattedAnswer = (content: string, message: Message) => {
    // 如果有 message.sources，移除 content 中的【数据来源】部分，避免重复
    let cleanContent = content;
    if (message.sources && message.sources.length > 0) {
      // 移除【数据来源】及其后面的内容
      cleanContent = content.replace(/【数据来源】.*?$/gs, '').trim();
      // 也移除【来源】（如果有）
      cleanContent = cleanContent.replace(/【来源】.*?$/gs, '').trim();
    }

    const sections = parseAnswerFormat(cleanContent);

    if (!sections.hasFormat) {
      // 没有标准格式，按原样显示
      return (
        <>
          {renderContent(cleanContent)}
          {/* 来源文档名称 - 顶格，颜色与标题一致 */}
          {message.sources && message.sources.length > 0 && (
            <div className="text-sm font-semibold text-chat-accent mt-3">
              【来源】{message.sources.map((source, index) => (
                <span key={source.id || index} className="font-normal text-chat-text">
                  {index > 0 && '、'}
                  {source.filename}
                </span>
              ))}
            </div>
          )}
        </>
      );
    }

    // 判断是两段式还是三段式
    const isTwoPartFormat = cleanContent.includes('【回答】') && !cleanContent.includes('【直接回答】');
    const titleText = isTwoPartFormat ? '【回答】' : '【直接回答】';

    return (
      <div className="space-y-3">
        {/* 【直接回答】或【回答】 */}
        {sections.directAnswer && (
          <div>
            <div className="text-sm font-semibold text-chat-accent mb-1">{titleText}</div>
            <div className="text-chat-text pl-4">
              {renderContent(sections.directAnswer)}
            </div>
          </div>
        )}

        {/* 【来源】 - 顶格显示，颜色与【回答】标题一致 */}
        {message.sources && message.sources.length > 0 && (
          <div>
            <div className="text-sm font-semibold text-chat-accent mb-1">【来源】</div>
            <div className="text-chat-text pl-4">
              {message.sources.map((source, index) => (
                <span key={source.id || index} className="text-sm">
                  {index > 0 && '、'}
                  {source.filename}
                </span>
              ))}
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
                    {renderFormattedAnswer(message.content, message)}
                  </div>

                  {/* AI消息的额外信息 */}
                  {message.role === 'assistant' && (
                    <div className="mt-4 pt-4 border-t border-chat-border">
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
            {/* 左侧：附件和回形针按钮 */}
            <div className="flex flex-col items-start gap-2">
              {/* 附件列表 - 在回形针按钮上方 */}
              {attachments.length > 0 && (
                <div className="flex flex-wrap gap-1.5 max-w-[200px]">
                  {attachments.map((attachment) => (
                    <div
                      key={attachment.attachment_id}
                      className="inline-flex items-center gap-1 bg-gray-100 hover:bg-gray-200 rounded px-2 py-1 text-xs text-gray-700 transition-colors max-w-[180px]"
                    >
                      <span className="flex-shrink-0 text-gray-500">
                        {getFileIcon(attachment.file_type)}
                      </span>
                      <span className="truncate flex-1" title={attachment.filename}>
                        {attachment.filename}
                      </span>
                      <button
                        onClick={() => handleRemoveAttachment(attachment.attachment_id)}
                        className="flex-shrink-0 text-gray-400 hover:text-gray-600 transition-colors p-0.5 hover:bg-gray-300 rounded"
                        title="删除"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* 回形针按钮 */}
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.xlsx,.xls,.txt,.jpg,.jpeg,.png"
                onChange={handleFileSelect}
                className="hidden"
              />
              <button
                onClick={handleFileUploadClick}
                disabled={uploadingFile}
                className="p-2 hover:bg-gray-100 rounded transition-colors flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed text-gray-500"
                title="上传附件 (支持PDF、Word、Excel、文本、图片)"
              >
                <Paperclip size={18} />
              </button>
            </div>

            {/* 中间：输入框 */}
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

            {/* 右侧：发送按钮 */}
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

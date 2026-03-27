/**
 * 移动端本地存储工具
 * 用于在浏览器 localStorage 中存储对话历史
 */

export interface LocalConversation {
  id: string;
  title: string;
  preview: string;
  timestamp: string;
  messageCount: number;
  messages: LocalMessage[];
}

export interface LocalMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: any[];
  relevanceScore?: number;
  reasoning?: string[];
}

const STORAGE_KEY = 'mobile_conversations';

// 获取所有对话
export function getLocalConversations(): LocalConversation[] {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

// 保存所有对话
function saveConversations(conversations: LocalConversation[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  } catch (e) {
    console.error('保存对话失败:', e);
  }
}

// 获取单个对话
export function getLocalConversation(conversationId: string): LocalConversation | null {
  const conversations = getLocalConversations();
  return conversations.find(c => c.id === conversationId) || null;
}

// 创建新对话
export function createLocalConversation(firstMessage: string): LocalConversation {
  const id = `local_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  const now = new Date().toISOString();

  const newConversation: LocalConversation = {
    id,
    title: firstMessage.substring(0, 30) + (firstMessage.length > 30 ? '...' : ''),
    preview: firstMessage.substring(0, 100) + (firstMessage.length > 100 ? '...' : ''),
    timestamp: now,
    messageCount: 1,
    messages: [{
      id: `${id}_msg_${Date.now()}`,
      role: 'user',
      content: firstMessage,
      timestamp: now,
    }],
  };

  const conversations = getLocalConversations();
  conversations.unshift(newConversation);
  saveConversations(conversations);

  return newConversation;
}

// 添加消息到对话
export function addMessageToConversation(
  conversationId: string,
  message: LocalMessage
): void {
  const conversations = getLocalConversations();
  const index = conversations.findIndex(c => c.id === conversationId);

  if (index !== -1) {
    conversations[index].messages.push(message);
    conversations[index].messageCount = conversations[index].messages.length;
    conversations[index].timestamp = new Date().toISOString();
    saveConversations(conversations);
  }
}

// 更新对话消息列表
export function updateConversationMessages(
  conversationId: string,
  messages: LocalMessage[]
): void {
  const conversations = getLocalConversations();
  const index = conversations.findIndex(c => c.id === conversationId);

  if (index !== -1) {
    conversations[index].messages = messages;
    conversations[index].messageCount = messages.length;
    conversations[index].timestamp = new Date().toISOString();
    saveConversations(conversations);
  }
}

// 删除对话
export function deleteLocalConversation(conversationId: string): void {
  const conversations = getLocalConversations();
  const filtered = conversations.filter(c => c.id !== conversationId);
  saveConversations(filtered);
}

// 清空所有对话
export function clearAllConversations(): void {
  localStorage.removeItem(STORAGE_KEY);
}

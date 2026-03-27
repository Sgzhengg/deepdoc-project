import { create } from 'zustand';
import type { Message, Conversation, Document, KnowledgeBaseStatus } from '@/types';

interface AppState {
  // 当前活动标签
  activeTab: 'chat' | 'documents' | 'settings';
  setActiveTab: (tab: 'chat' | 'documents' | 'settings') => void;

  // 聊天相关状态
  messages: Message[];
  conversations: Conversation[];
  currentConversationId: string | null;
  isLoading: boolean;

  addMessage: (message: Message) => void;
  setMessages: (messages: Message[]) => void;
  clearMessages: () => void;
  setConversations: (conversations: Conversation[]) => void;
  setCurrentConversation: (conversationId: string | null) => void;
  addOrUpdateConversation: (conversation: Conversation) => void;
  startNewConversation: () => void;
  setLoading: (loading: boolean) => void;
  deleteConversation: (conversationId: string) => void;
  batchDeleteConversations: (conversationIds: string[]) => void;

  // 会话批量选择状态
  selectedConversationIds: string[];
  toggleConversationSelection: (conversationId: string) => void;
  clearConversationSelection: () => void;
  selectAllConversations: () => void;

  // 文档管理相关状态
  documents: Document[];
  kbStatus: KnowledgeBaseStatus | null;
  selectedDocuments: string[];
  rightPanelOpen: boolean;

  setDocuments: (documents: Document[]) => void;
  setKbStatus: (status: KnowledgeBaseStatus) => void;
  toggleDocumentSelection: (documentId: string) => void;
  clearDocumentSelection: () => void;
  setRightPanelOpen: (open: boolean) => void;

  // 左侧边栏状态
  leftSidebarOpen: boolean;
  setLeftSidebarOpen: (open: boolean) => void;
}

export const useStore = create<AppState>((set) => ({
  // 初始状态
  activeTab: 'chat',
  messages: [],
  conversations: [],
  currentConversationId: null,
  isLoading: false,
  documents: [],
  kbStatus: null,
  selectedDocuments: [],
  rightPanelOpen: false,
  leftSidebarOpen: true,
  selectedConversationIds: [],

  // Actions
  setActiveTab: (tab) => set({ activeTab: tab }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  setMessages: (messages) => set({ messages }),

  setConversations: (conversations) => set({ conversations }),

  setCurrentConversation: (conversationId) => set({ currentConversationId: conversationId }),

  addOrUpdateConversation: (conversation) =>
    set((state) => {
      const existingIndex = state.conversations.findIndex((c) => c.id === conversation.id);
      if (existingIndex >= 0) {
        // 更新现有会话
        const updated = [...state.conversations];
        updated[existingIndex] = conversation;
        return { conversations: updated };
      } else {
        // 添加新会话到列表开头
        return { conversations: [conversation, ...state.conversations] };
      }
    }),

  setLoading: (loading) => set({ isLoading: loading }),

  clearMessages: () => set({ messages: [] }),

  startNewConversation: () => set({ currentConversationId: null, messages: [] }),

  deleteConversation: (conversationId) =>
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== conversationId),
      currentConversationId:
        state.currentConversationId === conversationId ? null : state.currentConversationId,
    })),

  batchDeleteConversations: (conversationIds) =>
    set((state) => ({
      conversations: state.conversations.filter((c) => !conversationIds.includes(c.id)),
      currentConversationId: conversationIds.includes(state.currentConversationId || '')
        ? null
        : state.currentConversationId,
      selectedConversationIds: [],
    })),

  toggleConversationSelection: (conversationId) =>
    set((state) => ({
      selectedConversationIds: state.selectedConversationIds.includes(conversationId)
        ? state.selectedConversationIds.filter((id) => id !== conversationId)
        : [...state.selectedConversationIds, conversationId],
    })),

  clearConversationSelection: () => set({ selectedConversationIds: [] }),

  selectAllConversations: () =>
    set((state) => ({
      selectedConversationIds: state.conversations.map((c) => c.id),
    })),

  setDocuments: (documents) => set({ documents }),

  setKbStatus: (status) => set({ kbStatus: status }),

  toggleDocumentSelection: (documentId) =>
    set((state) => ({
      selectedDocuments: state.selectedDocuments.includes(documentId)
        ? state.selectedDocuments.filter((id) => id !== documentId)
        : [...state.selectedDocuments, documentId],
    })),

  clearDocumentSelection: () => set({ selectedDocuments: [] }),

  setRightPanelOpen: (open) => set({ rightPanelOpen: open }),

  setLeftSidebarOpen: (open) => set({ leftSidebarOpen: open }),
}));

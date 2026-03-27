import React from 'react';
import { ChevronRight, ChevronLeft } from 'lucide-react';
import { useStore } from '@/store/useStore';
import LeftSidebar from '../LeftSidebar/LeftSidebar';
import ChatArea from '../ChatArea/ChatArea';
import RightSidebar from '../RightSidebar/RightSidebar';

const MainLayout: React.FC = () => {
  const { leftSidebarOpen, rightPanelOpen, setLeftSidebarOpen, setRightPanelOpen } = useStore();

  return (
    <div className="flex h-screen bg-chat-bg text-chat-text overflow-hidden">
      {/* 左侧边栏 */}
      <div
        className={`transition-all duration-300 ease-in-out bg-chat-bg border-r border-chat-border flex-shrink-0 ${
          leftSidebarOpen ? 'w-80' : 'w-0'
        } overflow-hidden`}
      >
        {leftSidebarOpen && <LeftSidebar />}
      </div>

      {/* 左侧展开/隐藏按钮 */}
      {!leftSidebarOpen && (
        <button
          onClick={() => setLeftSidebarOpen(true)}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-10 bg-chat-bg border border-chat-border p-2 rounded-r-lg hover:bg-chat-bg-secondary transition-colors"
          title="打开历史对话"
        >
          <ChevronRight className="text-chat-text" size={20} />
        </button>
      )}

      {/* 中间聊天区域 */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* 左侧收起按钮（在聊天区域左侧） */}
        {leftSidebarOpen && (
          <button
            onClick={() => setLeftSidebarOpen(false)}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-10 bg-chat-bg border border-chat-border p-2 rounded-r-lg hover:bg-chat-bg-secondary transition-colors"
            title="收起历史对话"
          >
            <ChevronLeft className="text-chat-text" size={20} />
          </button>
        )}

        {/* 右侧收起按钮（在聊天区域右侧） */}
        {rightPanelOpen && (
          <button
            onClick={() => setRightPanelOpen(false)}
            className="absolute right-0 top-1/2 -translate-y-1/2 z-10 bg-chat-bg border border-chat-border p-2 rounded-l-lg hover:bg-chat-bg-secondary transition-colors"
            title="收起管理面板"
          >
            <ChevronRight className="text-chat-text" size={20} />
          </button>
        )}

        <ChatArea />
      </div>

      {/* 右侧管理面板 */}
      <div
        className={`transition-all duration-300 ease-in-out bg-chat-bg border-l border-chat-border flex-shrink-0 ${
          rightPanelOpen ? 'w-80' : 'w-0'
        } overflow-hidden`}
      >
        {rightPanelOpen && <RightSidebar />}
      </div>

      {/* 右侧展开按钮（当侧边栏收起时显示） */}
      {!rightPanelOpen && (
        <button
          onClick={() => setRightPanelOpen(true)}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-10 bg-chat-bg border border-chat-border p-2 rounded-l-lg hover:bg-chat-bg-secondary transition-colors"
          title="打开管理面板"
        >
          <ChevronLeft className="text-chat-text" size={20} />
        </button>
      )}
    </div>
  );
};

export default MainLayout;

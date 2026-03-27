import React, { useState } from 'react';
import { Menu, X, MessageSquare, History } from 'lucide-react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import './MobileLayout.css';

const MobileLayout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const isChatPage = location.pathname === '/' || location.pathname.startsWith('/') && !location.pathname.startsWith('/history');

  return (
    <div className="mobile-layout">
      {/* 顶部导航栏 */}
      <header className="mobile-header">
        <div className="mobile-header-left">
          <button
            className="menu-btn"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="菜单"
          >
            {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
          <h1 className="mobile-title">渠道业务助手</h1>
        </div>
      </header>

      {/* 侧边栏遮罩 */}
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}

      {/* 侧边栏 */}
      <aside className={`mobile-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <nav className="sidebar-nav">
          <div
            className={`nav-item ${isChatPage ? 'active' : ''}`}
            onClick={() => {
              navigate('/');
              setSidebarOpen(false);
            }}
          >
            <MessageSquare size={20} />
            <span>智能问答</span>
          </div>
          <div
            className={`nav-item ${location.pathname === '/history' ? 'active' : ''}`}
            onClick={() => {
              navigate('/history');
              setSidebarOpen(false);
            }}
          >
            <History size={20} />
            <span>历史对话</span>
          </div>
        </nav>

        <div className="sidebar-footer">
          <p className="footer-text">渠道门店专用</p>
        </div>
      </aside>

      {/* 主内容区 */}
      <main className="mobile-main">
        <Outlet />
      </main>
    </div>
  );
};

export default MobileLayout;

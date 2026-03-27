# 运营商渠道业务AI智能查询与分析系统 - 项目总结

## 项目概述

这是一个完整的 React + TypeScript 前端项目，实现了仿照 ChatGPT 风格的 PC 端 Web 管理员界面，用于运营商渠道业务 AI 智能查询与分析系统。

## 已创建的文件列表

### 配置文件
1. [package.json](./package.json) - 项目依赖和脚本配置
2. [tsconfig.json](./tsconfig.json) - TypeScript 编译配置
3. [tsconfig.node.json](./tsconfig.node.json) - Node 环境 TypeScript 配置
4. [tailwind.config.js](./tailwind.config.js) - Tailwind CSS 主题配置
5. [postcss.config.js](./postcss.config.js) - PostCSS 配置
6. [vite.config.ts](./vite.config.ts) - Vite 构建工具配置
7. [index.html](./index.html) - HTML 入口模板
8. [.gitignore](./.gitignore) - Git 忽略规则
9. [.env.example](./.env.example) - 环境变量模板

### 源代码文件
1. [src/main.tsx](./src/main.tsx) - 应用入口
2. [src/App.tsx](./src/App.tsx) - 根组件
3. [src/index.css](./src/index.css) - 全局样式
4. [src/vite-env.d.ts](./src/vite-env.d.ts) - Vite 类型声明

### 类型定义
1. [src/types/index.ts](./src/types/index.ts) - 所有 TypeScript 类型定义
   - Message (消息)
   - Source (来源文档)
   - Conversation (会话)
   - Document (文档)
   - KnowledgeBaseStatus (知识库状态)
   - OperationLog (操作日志)
   - API 请求/响应类型

### API 服务层
1. [src/services/api.ts](./src/services/api.ts) - HTTP API 服务
   - chatApi (聊天相关)
   - documentApi (文档管理)
   - knowledgeBaseApi (知识库管理)
   - 请求/响应拦截器

### 状态管理
1. [src/store/useStore.ts](./src/store/useStore.ts) - Zustand 全局状态
   - 聊天状态
   - 会话管理
   - 文档管理
   - UI 状态

### 组件

#### 布局组件
1. [src/components/Layout/MainLayout.tsx](./src/components/Layout/MainLayout.tsx) - 主布局
   - 三栏布局结构
   - 左侧边栏容器
   - 中间聊天区域容器
   - 右侧面板容器

#### 左侧边栏
1. [src/components/LeftSidebar/LeftSidebar.tsx](./src/components/LeftSidebar/LeftSidebar.tsx) - 左侧边栏
   - 系统标题显示
   - 功能切换按钮 (AI问答、文档管理、系统设置)
   - 会话历史列表
   - 新建对话按钮

#### 聊天区域
1. [src/components/ChatArea/ChatArea.tsx](./src/components/ChatArea/ChatArea.tsx) - 聊天区域
   - 消息展示（用户/AI气泡）
   - Markdown 渲染
   - 代码高亮
   - 来源文档展示
   - 推理过程展示
   - 相关度评分
   - 消息输入框
   - 快捷键支持 (Ctrl+Enter)

#### 右侧面板
1. [src/components/RightPanel/RightPanel.tsx](./src/components/RightPanel/RightPanel.tsx) - 文档管理面板
   - 文档上传区域（拖拽支持）
   - 上传进度显示
   - 文档列表展示
   - 批量删除功能
   - 知识库统计卡片
   - 知识库操作按钮
   - 操作日志展示

### 文档
1. [README.md](./README.md) - 项目说明文档
2. [QUICKSTART.md](./QUICKSTART.md) - 快速开始指南

## 技术栈

### 核心框架
- React 18 - UI 框架
- TypeScript - 类型安全
- Vite 5 - 构建工具

### 样式和UI
- Tailwind CSS - 样式框架
- Lucide React - 图标库
- 自定义主题颜色

### 功能库
- Axios - HTTP 客户端
- React Markdown - Markdown 渲染
- React Syntax Highlighter - 代码高亮
- Zustand - 状态管理

### 开发工具
- ESLint - 代码检查
- PostCSS - CSS 处理
- Autoprefixer - CSS 兼容性

## 主要功能

### 1. 聊天功能
- ✅ 发送消息
- ✅ 接收 AI 回答
- ✅ 消息历史记录
- ✅ Markdown 渲染
- ✅ 代码高亮
- ✅ 来源文档展示
- ✅ 推理过程展示
- ✅ 相关度评分
- ✅ 快捷键支持

### 2. 文档管理
- ✅ 文档上传（拖拽）
- ✅ 上传进度显示
- ✅ 文档列表展示
- ✅ 文档状态显示
- ✅ 单个删除
- ✅ 批量删除
- ✅ 文件类型验证

### 3. 知识库管理
- ✅ 知识库状态统计
- ✅ 文档数量统计
- ✅ 数据块统计
- ✅ 向量库状态
- ✅ 清空知识库
- ✅ 重置向量库
- ✅ 操作日志

### 4. 会话管理
- ✅ 新建对话
- ✅ 会话历史
- ✅ 切换会话
- ✅ 删除会话
- ✅ 会话预览

### 5. UI 交互
- ✅ 三栏布局
- ✅ 侧边栏可折叠
- ✅ 右侧面板可收起
- ✅ 响应式设计
- ✅ 加载动画
- ✅ 滚动优化

## 颜色主题

| 用途 | 颜色值 |
|------|--------|
| 主背景 | #343541 |
| 次级背景 | #444654 |
| 输入框背景 | #40414f |
| 文本颜色 | #ececf1 |
| 强调色（绿色） | #10a37f |
| 边框颜色 | #565869 |
| 用户气泡 | #343541 |
| AI 气泡 | #444654 |

## API 接口

### 聊天相关
```
POST   /api/chat                        发送消息
GET    /api/conversations               获取会话列表
DELETE /api/conversations/:id           删除会话
GET    /api/conversations/:id/messages  获取会话消息
```

### 文档管理
```
POST   /api/documents/ingest            上传文档
GET    /api/documents                   获取文档列表
DELETE /api/documents/:id               删除文档
DELETE /api/documents/batch             批量删除文档
POST   /api/documents/:id/reprocess     重新处理文档
```

### 知识库管理
```
GET    /api/kb/status                   获取知识库状态
DELETE /api/kb/clear                    清空知识库
POST   /api/kb/reset                    重置向量库
GET    /api/kb/logs                     获取操作日志
```

## 快速开始

```bash
# 1. 安装依赖
cd frontend
npm install

# 2. 启动开发服务器
npm run dev

# 3. 访问应用
# http://localhost:3000
```

## 项目特色

1. **完全类型安全** - 使用 TypeScript，所有类型都有明确定义
2. **现代化技术栈** - React 18 + Vite 5 + Tailwind CSS
3. **代码高亮** - 支持多种语言的语法高亮
4. **状态管理** - 使用 Zustand，简洁高效
5. **响应式设计** - 最小宽度 1200px
6. **主题定制** - ChatGPT 风格深色主题
7. **交互友好** - 拖拽上传、快捷键、动画效果

## 浏览器支持

- Chrome (推荐)
- Firefox
- Edge
- Safari

## 开发建议

1. 保持组件单一职责
2. 使用 TypeScript 类型检查
3. 遵循 React Hooks 规则
4. 使用 Tailwind 工具类而不是自定义 CSS
5. 保持代码简洁，避免过度工程化

## 许可证

MIT License

## 总结

这是一个功能完整、代码规范、易于维护的 React + TypeScript 项目，实现了运营商渠道业务 AI 智能查询与分析系统的前端界面。项目采用现代化的技术栈，具有良好的类型安全性和开发体验。

# 运营商渠道业务AI智能查询与分析系统 - 前端

这是一个仿照 ChatGPT 风格的 PC 端 Web 管理员界面，用于运营商渠道业务 AI 智能查询与分析系统。

## 技术栈

- **React 18** - 前端框架
- **TypeScript** - 类型安全
- **Tailwind CSS** - 样式框架
- **Vite** - 构建工具
- **Axios** - HTTP 请求
- **React Markdown** - Markdown 渲染
- **Zustand** - 状态管理
- **Lucide React** - 图标库

## 项目结构

```
frontend/
├── src/
│   ├── components/          # React 组件
│   │   ├── Layout/         # 布局组件
│   │   ├── LeftSidebar/    # 左侧边栏
│   │   ├── ChatArea/       # 聊天区域
│   │   ├── RightPanel/     # 右侧文档管理面板
│   │   └── Common/         # 通用组件
│   ├── services/           # API 服务层
│   ├── store/              # 状态管理
│   ├── types/              # TypeScript 类型定义
│   ├── hooks/              # 自定义 Hooks
│   ├── utils/              # 工具函数
│   ├── App.tsx             # 应用根组件
│   ├── main.tsx            # 应用入口
│   └── index.css           # 全局样式
├── public/                 # 静态资源
├── index.html              # HTML 模板
├── package.json            # 项目依赖
├── tsconfig.json           # TypeScript 配置
├── tailwind.config.js      # Tailwind CSS 配置
├── vite.config.ts          # Vite 配置
└── README.md               # 项目说明
```

## 功能特性

### 1. 三栏布局
- **左侧边栏** (260px): 功能导航和会话历史
- **中间主区域**: 聊天交互界面
- **右侧面板** (可折叠 280px): 文档管理和知识库操作

### 2. 左侧边栏功能
- 系统标题显示
- 功能切换按钮 (AI问答、文档管理、系统设置)
- 会话历史列表 (可滚动、支持删除)
- 新建对话按钮

### 3. 右侧文档管理面板
- **文档上传**: 支持拖拽上传、进度显示
- **文档列表**: 表格展示、状态标签、批量操作
- **知识库管理**: 统计卡片、操作按钮、操作日志

### 4. AI 聊天区域
- **对话展示**: 消息气泡、Markdown 渲染、代码高亮
- **AI 回答增强**: 相关度评分、来源文档、推理过程
- **输入区域**: 多行输入、快捷键支持 (Ctrl+Enter)

## 颜色主题

- 主背景: #343541 (深色模式)
- 次级背景: #444654
- 输入框背景: #40414f
- 文本颜色: #ececf1
- 强调色: #10a37f (ChatGPT 绿)
- 边框: #565869

## 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 3. 构建生产版本

```bash
npm run build
```

### 4. 预览生产构建

```bash
npm run preview
```

## 后端接口对接

系统已配置以下 API 接口：

### 聊天相关
- `POST /api/chat` - 发送消息
- `GET /api/conversations` - 获取会话历史
- `DELETE /api/conversations/:id` - 删除会话
- `GET /api/conversations/:id/messages` - 获取会话详情

### 文档管理
- `POST /api/documents/ingest` - 上传文档
- `GET /api/documents` - 获取文档列表
- `DELETE /api/documents/:id` - 删除文档
- `DELETE /api/documents/batch` - 批量删除文档
- `POST /api/documents/:id/reprocess` - 重新处理文档

### 知识库管理
- `GET /api/kb/status` - 获取知识库状态
- `DELETE /api/kb/clear` - 清空知识库
- `POST /api/kb/reset` - 重置向量库
- `GET /api/kb/logs?limit=10` - 获取操作日志

## 配置说明

### API 代理配置

在 `vite.config.ts` 中已配置代理：

```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

如需修改后端地址，请更改 `target` 值。

### 环境变量

创建 `.env` 文件（可选）：

```env
VITE_API_URL=http://localhost:8000
```

## 响应式设计

- 最小宽度: 1200px
- 侧边栏可折叠
- 右侧面板可收起

## 开发注意事项

1. **类型安全**: 项目使用 TypeScript，确保所有组件和函数都有正确的类型定义
2. **状态管理**: 使用 Zustand 进行全局状态管理，避免 prop drilling
3. **API 调用**: 所有 API 调用统一通过 `services/api.ts` 进行
4. **错误处理**: API 调用已添加错误拦截器，统一处理错误

## 浏览器支持

- Chrome (推荐)
- Firefox
- Edge
- Safari

## 许可证

MIT License

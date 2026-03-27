# 快速开始指南

## 安装步骤

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

服务器将在 http://localhost:3000 启动

### 3. 构建生产版本

```bash
npm run build
```

构建后的文件将在 `dist` 目录中

## 项目结构说明

```
frontend/
├── src/
│   ├── components/
│   │   ├── Layout/
│   │   │   └── MainLayout.tsx          # 主布局组件（三栏布局）
│   │   ├── LeftSidebar/
│   │   │   └── LeftSidebar.tsx         # 左侧边栏（导航和历史）
│   │   ├── ChatArea/
│   │   │   └── ChatArea.tsx            # 中间聊天区域
│   │   └── RightPanel/
│   │       └── RightPanel.tsx          # 右侧文档管理面板
│   ├── services/
│   │   └── api.ts                      # API 服务层
│   ├── store/
│   │   └── useStore.ts                 # Zustand 状态管理
│   ├── types/
│   │   └── index.ts                    # TypeScript 类型定义
│   ├── App.tsx                         # 根组件
│   ├── main.tsx                        # 应用入口
│   └── index.css                       # 全局样式
├── index.html
├── package.json
├── tsconfig.json
├── tailwind.config.js
└── vite.config.ts
```

## 主要功能

### 1. 左侧边栏
- **功能切换**: AI问答、文档管理、系统设置
- **会话历史**: 显示所有历史对话
- **新建对话**: 创建新的对话会话

### 2. 中间聊天区域
- **消息展示**: 用户和AI消息的气泡展示
- **Markdown渲染**: 支持富文本和代码高亮
- **来源文档**: 显示AI回答的来源
- **推理过程**: 展示AI的推理步骤
- **相关度评分**: 显示答案的可信度

### 3. 右侧文档管理面板
- **文档上传**: 拖拽上传或点击上传
- **文档列表**: 显示所有已上传的文档
- **批量操作**: 支持批量删除文档
- **知识库管理**: 查看知识库状态和统计
- **操作日志**: 查看最近的操作记录

## 后端对接

项目已配置代理到 `http://localhost:8000`，确保后端服务在该端口运行。

如需修改后端地址，编辑 `vite.config.ts`：

```typescript
server: {
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://your-backend-url',
      changeOrigin: true,
    },
  },
}
```

## 快捷键

- **Ctrl + Enter**: 发送消息

## 主题颜色

- 主背景: #343541
- 次级背景: #444654
- 输入框: #40414f
- 强调色: #10a37f（绿色）

## 开发提示

1. 使用 TypeScript 进行类型检查
2. 使用 Zustand 进行状态管理
3. 所有 API 调用都在 `services/api.ts` 中
4. 组件使用 Tailwind CSS 进行样式设计

## 故障排除

### 端口冲突

如果 3000 端口被占用，可以修改 `vite.config.ts`：

```typescript
server: {
  port: 3001, // 改为其他端口
}
```

### API 连接失败

检查后端服务是否正在运行，并确认代理配置正确。

### 依赖安装失败

尝试清除缓存后重新安装：

```bash
rm -rf node_modules package-lock.json
npm install
```

## 部署

### 构建生产版本

```bash
npm run build
```

### 预览生产版本

```bash
npm run preview
```

### 部署到服务器

将 `dist` 目录上传到服务器，并配置 Web 服务器（如 Nginx）提供静态文件服务。

示例 Nginx 配置：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 技术支持

如有问题，请查看：
- [README.md](./README.md) - 详细文档
- [Vite 文档](https://vitejs.dev/)
- [React 文档](https://react.dev/)
- [Tailwind CSS 文档](https://tailwindcss.com/)

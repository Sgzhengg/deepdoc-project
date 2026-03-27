# DeepDoc 项目快速启动指南

## 项目简介

智能文档处理系统 - 基于 DeepDoctection 和 Qdrant 的文档分析平台。

**核心特性：**
- ✅ DeepDoctection 文档解析
- ✅ 向量检索（Qdrant + sentence-transformers）
- ✅ 混合检索（BM25 + 向量）
- ✅ Agentic RAG 系统
- ✅ 表格提取和分析
- ✅ 知识库管理

## 快速启动

### 前置要求

- Docker
- Docker Compose

### 一键启动

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

### 手动启动

```bash
# 创建数据目录
mkdir -p data/documents data/audit_logs data/backups

# 启动服务
docker-compose -f docker-compose-complete.yml up -d

# 查看日志
docker-compose -f docker-compose-complete.yml logs -f

# 停止服务
docker-compose -f docker-compose-complete.yml down
```

## 服务访问

启动成功后，可以访问以下服务：

| 服务 | 地址 | 说明 |
|------|------|------|
| **FastAPI 文档** | http://localhost:8000/docs | Swagger UI 交互式文档 |
| **FastAPI ReDoc** | http://localhost:8000/redoc | ReDoc 文档 |
| **Qdrant 控制台** | http://localhost:6333/dashboard | 向量数据库管理 |

## 服务架构

系统包含3个核心服务：

1. **backend** - FastAPI 后端服务
   - Python 3.10
   - DeepDoctection 文档分析
   - 向量检索和混合检索
   - Agentic RAG

2. **qdrant** - 向量数据库
   - 存储文档向量
   - 高性能相似度搜索

3. **ollama** - LLM 服务
   - 本地大语言模型
   - 支持 Qwen2.5 等模型

## 下一步

### 1. 下载 LLM 模型

```bash
docker exec -it deepdoc-ollama ollama pull qwen2.5-7b-instruct-1m
```

### 2. 测试 API

访问 http://localhost:8000/docs 进行交互式测试

### 3. 上传文档测试

使用 `/analyze` 端点上传文档进行解析

## 技术栈

- **后端框架**: FastAPI
- **文档分析**: DeepDoctection
- **向量数据库**: Qdrant
- **嵌入模型**: BAAI/bge-small-zh-v1.5
- **LLM**: Ollama (Qwen2.5)
- **容器**: Docker + Docker Compose

## 目录结构

```
deepdoc-project/
├── backend/               # 后端服务
│   ├── agents/           # Agentic RAG 智能体
│   ├── storage/          # 存储层实现
│   ├── main.py          # API 入口
│   ├── Dockerfile       # Docker 配置
│   └── requirements.txt # Python 依赖
├── data/                # 数据目录
│   ├── documents/      # 文档存储
│   ├── audit_logs/     # 审计日志
│   └── backups/        # 备份
├── docker/              # Docker 配置
├── docs/               # 项目文档
└── frontend/           # 前端（待开发）
```

## 常见问题

### Q: 如何更换 LLM 模型？

A: 修改 `docker-compose-complete.yml` 中的 `LLM_MODEL` 环境变量，然后重启服务。

### Q: 如何启用 GPU 加速？

A: 需要安装 NVIDIA Container Toolkit，并在 docker-compose.yml 中添加 GPU 配置。

### Q: 服务启动失败怎么办？

A: 检查日志：
```bash
docker-compose -f docker-compose-complete.yml logs backend
```

## 许可证

MIT License

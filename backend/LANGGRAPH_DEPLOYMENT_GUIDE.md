# DeepDoc LangGraph 部署指南

## 概述

本文档介绍基于LangGraph的多Agent系统的部署和使用方法。

## 新架构特性

### 核心改进

1. **统一入口** - 所有AI交互通过 `/api/chat` 接口
2. **智能路由** - 自动识别意图并调用合适的Agent
3. **Self-RAG** - 自动评估和优化检索/生成质量
4. **多Agent协作** - IntentAgent → RetrievalAgent → ReasoningAgent → GenerateAgent
5. **状态机编排** - 基于LangGraph的工作流控制

### 前端只有2个入口

1. **POST** `/api/documents/ingest` - 文档入库
2. **POST** `/api/chat` - AI聊天

## 环境要求

### 软件依赖

- Python 3.9+
- Ollama (用于运行本地LLM)
- Qdrant (向量数据库)
- Redis (可选，用于会话存储)

### 安装LangGraph依赖

```bash
cd backend
pip install -r requirements.txt
```

新增的LangGraph相关依赖：
- langgraph>=0.2.0
- langchain>=0.3.0
- langchain-core>=0.3.0
- langchain-ollama>=0.2.0
- langchain-community>=0.3.0
- ollama>=0.4.0

## 配置

### 1. 安装和启动Ollama

```bash
# 安装Ollama (Linux)
curl -fsSL https://ollama.com/install.sh | sh

# 或使用Docker
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama

# 下载模型
ollama pull qwen2.5:7b

# 验证
ollama list
```

### 2. 环境变量配置

创建 `.env` 文件：

```bash
# Ollama配置
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b

# Qdrant配置
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Redis配置（可选）
REDIS_HOST=localhost
REDIS_PORT=6379

# CORS配置
ALLOWED_ORIGINS=*
```

### 3. 启动Qdrant

```bash
# 使用Docker
docker run -d -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    --name qdrant \
    qdrant/qdrant
```

### 4. 启动后端服务

```bash
cd backend

# 方式1: 直接运行
python main.py

# 方式2: 使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 方式3: 使用Docker (推荐)
docker build -t deepdoc-backend .
docker run -d -p 8000:8000 \
    -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
    -e QDRANT_HOST=qdrant \
    --name deepdoc-backend \
    deepdoc-backend
```

## API使用指南

### 1. 文档入库

**接口**: `POST /api/documents/ingest`

**请求**:
```bash
curl -X POST "http://localhost:8000/api/documents/ingest" \
    -F "file=@document.pdf"
```

**响应**:
```json
{
  "success": true,
  "document_id": "uuid-xxx",
  "filename": "document.pdf",
  "chunks_count": 42,
  "tables_extracted": 3,
  "status": "indexed"
}
```

**支持格式**: PDF, DOCX, XLSX

### 2. AI聊天（统一入口）

**接口**: `POST /api/chat`

**请求**:
```json
{
  "message": "59元套餐的分成比例是多少？",
  "session_id": "optional-session-id",
  "stream": false,
  "config": {
    "max_iterations": 3
  }
}
```

**响应**:
```json
{
  "success": true,
  "session_id": "session-uuid",
  "answer": "根据渠道政策文档，59元套餐的分成比例是...",
  "reasoning": [
    "🔍 意图识别: 表格查询",
    "📝 查询类型: 简单查询",
    "🏷️  提取实体: 2个 - ['59', '分成']",
    "📋 检索策略: table",
    "🔎 开始检索: 策略=table",
    "📊 检索到 3 个文档",
    "⭐ 质量评分: 0.85",
    "🧠 开始推理分析",
    "✅ 综合完成，生成最终答案"
  ],
  "sources": [
    {
      "type": "table",
      "content": "59元套餐的分成比例为...",
      "confidence": 0.95
    }
  ],
  "confidence": 0.87,
  "metadata": {
    "intent": "table_query",
    "query_type": "simple",
    "retrieval_strategy": "table",
    "docs_retrieved": 3,
    "tables_used": 2,
    "iterations": 1
  }
}
```

### 3. 健康检查

**接口**: `GET /api/chat/health`

**响应**:
```json
{
  "status": "healthy",
  "service": "ChatService",
  "initialized": true,
  "components": {
    "llm": { "status": "healthy" },
    "master_graph": { "status": "healthy" },
    "hybrid_retriever": { "status": "healthy" },
    "table_analyzer": { "status": "healthy" }
  }
}
```

## LangGraph工作流

### Agent执行流程

```
用户查询
    ↓
IntentAgent (意图识别)
    ↓
PlanNode (规划检索策略)
    ↓
RetrievalAgent (检索)
    ↓
[评估检索质量] → 质量不足 → 重新检索 (循环)
    ↓ 质量良好
ReasoningAgent (推理分析)
    ↓
GenerateAgent (生成答案)
    ↓
ReflectNode (评估答案质量) → 质量不足 → 重新推理 (循环)
    ↓ 质量良好
SynthesisAgent (综合)
    ↓
返回结果
```

### 意图类型

| 意图 | 说明 | 示例 |
|------|------|------|
| `search` | 文档搜索 | "查找关于人工智能的文档" |
| `table_query` | 表格查询 | "59元套餐的分成是多少" |
| `analyze` | 文档分析 | "分析这个表格的内容" |
| `compare` | 对比分析 | "对比59元和129元套餐" |
| `calculate` | 计算 | "计算总费用" |
| `status` | 状态查询 | "知识库有多少文档" |
| `general` | 通用问答 | 其他问题 |

### 检索策略

| 策略 | 使用场景 | 方法 |
|------|---------|------|
| `vector` | 简单查询 | 纯向量语义检索 |
| `hybrid` | 复杂查询 | 向量 + BM25混合检索 |
| `table` | 表格查询 | 专门的表格检索 |

## 测试

### 1. 测试文档入库

```bash
# 上传测试文档
curl -X POST "http://localhost:8000/api/documents/ingest" \
    -F "file=@test.pdf"

# 查看知识库状态
curl "http://localhost:8000/api/documents/status"
```

### 2. 测试AI聊天

```bash
# 简单查询
curl -X POST "http://localhost:8000/api/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "知识库里有多少文档？"}'

# 表格查询
curl -X POST "http://localhost:8000/api/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "59元套餐的分成比例是多少？"}'

# 文档搜索
curl -X POST "http://localhost:8000/api/chat" \
    -H "Content-Type: application/json" \
    -d '{"message": "搜索关于费用的文档"}'
```

### 3. 使用Python测试

```python
import requests

# 文档入库
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/documents/ingest",
        files={"file": f}
    )
    print(response.json())

# AI聊天
response = requests.post(
    "http://localhost:8000/api/chat",
    json={
        "message": "59元套餐的分成比例是多少？"
    }
)
print(response.json())
```

## 故障排查

### 问题1: ChatService初始化失败

**症状**: 启动时显示"ChatService初始化失败"

**解决**:
1. 检查Ollama是否运行: `ollama list`
2. 检查模型是否下载: `ollama pull qwen2.5:7b`
3. 检查环境变量: `echo $OLLAMA_BASE_URL`

### 问题2: 检索失败

**症状**: 返回"检索失败"或没有相关文档

**解决**:
1. 检查Qdrant是否运行: `curl http://localhost:6333/collections`
2. 检查是否已入库文档: `curl http://localhost:8000/api/documents/status`
3. 确认向量模型已加载

### 问题3: 导入错误

**症状**: `ModuleNotFoundError: No module named 'langgraph'`

**解决**:
```bash
pip install -r requirements.txt
# 或单独安装
pip install langgraph langchain langchain-ollama
```

## 性能优化

### 1. 减少迭代次数

```json
{
  "message": "查询内容",
  "config": {
    "max_iterations": 1  // 从默认3减少到1
  }
}
```

### 2. 使用更小的模型

```bash
ollama pull qwen2.5:3b  # 使用3B模型
# 设置环境变量
LLM_MODEL=qwen2.5:3b
```

### 3. 调整检索参数

在 `config` 中设置:
```json
{
  "top_k": 5,           // 减少检索数量
  "score_threshold": 0.5 // 提高阈值
}
```

## 生产部署

### Docker Compose部署

```yaml
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - ./qdrant_storage:/qdrant/storage

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

  deepdoc-backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    depends_on:
      - qdrant
      - ollama
```

启动:
```bash
docker-compose up -d
```

## 监控和日志

### 查看日志

```bash
# 查看应用日志
docker logs deepdoc-backend -f

# 查看特定组件的日志
docker logs deepdoc-backend | grep "IntentAgent"
docker logs deepdoc-backend | grep "RetrievalAgent"
```

### 性能监控

响应中包含 `metadata` 字段，可用于监控：
- `docs_retrieved`: 检索到的文档数量
- `tables_used`: 使用的表格数量
- `iterations`: 迭代次数
- `confidence`: 置信度

## 下一步

1. **前端集成** - 开发前端UI，只有2个入口
2. **流式输出** - 实现SSE流式返回
3. **会话管理** - 集成Redis存储会话历史
4. **性能优化** - 缓存、批处理、异步优化
5. **监控集成** - LangSmith监控

## 参考资料

- [LangGraph文档](https://langchain-ai.github.io/langgraph/)
- [LangChain文档](https://python.langchain.com/)
- [Ollama文档](https://ollama.com/docs)
- [Qdrant文档](https://qdrant.tech/documentation/)

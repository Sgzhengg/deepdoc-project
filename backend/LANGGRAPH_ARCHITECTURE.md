# DeepDoc LangGraph 多Agent架构设计

## 架构概览

基于LangGraph的Agentic RAG系统，用于渠道业务智能查询与分析。

```
┌─────────────────────────────────────────────────────────────┐
│                      前端应用（2个入口）                      │
├─────────────────────────────────────────────────────────────┤
│  1. POST /api/documents/ingest  - 文档入库                   │
│  2. POST /api/chat              - AI聊天（统一入口）          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph 工作流引擎                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          StateGraph (AgentState 状态机)               │  │
│  │                                                        │  │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐       │  │
│  │  │   入口    │ →  │ 意图识别  │ →  │  规划    │       │  │
│  │  │  start   │    │  intent  │    │  plan    │       │  │
│  │  └──────────┘    └──────────┘    └──────────┘       │  │
│  │                                           ↓           │  │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐       │  │
│  │  │   检索    │ ←  │ 决策分支  │ →  │  推理    │       │  │
│  │  │ retrieve │    │  branch  │    │  reason  │       │  │
│  │  └────┬─────┘    └──────────┘    └──────────┘       │  │
│  │       │                                                    │  │
│  │       │ [评估]                                             │  │
│  │       ↓                                                    │  │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐       │  │
│  │  │ 自我反思  │ →  │  重新检索  │    │  生成    │       │  │
│  │  │ reflect  │    │ reretrieve│    │ generate │       │  │
│  │  └──────────┘    └──────────┘    └────┬─────┘       │  │
│  │                                        ↓                 │  │
│  │                                  ┌──────────┐          │  │
│  │                                  │  综合答案  │          │  │
│  │                                  │  synthesize│         │  │
│  │                                  └────┬─────┘          │  │
│  │                                       ↓                 │  │
│  │                                  ┌──────────┐          │  │
│  │                                  │   END    │          │  │
│  │                                  └──────────┘          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    工具和资源层                               │
├─────────────────────────────────────────────────────────────┤
│  - 向量存储 (Qdrant)        - 表格分析器                      │
│  - 嵌入服务 (sentence-transformers)                         │
│  - 混合检索 (HybridRetriever)  - LLM服务 (Ollama)            │
│  - 文档处理器 (PaddleOCR, pypdf, python-docx)              │
│  - Redis会话存储                                             │
└─────────────────────────────────────────────────────────────┘
```

## AgentState 状态定义

```python
from typing import TypedDict, List, Dict, Any, Optional
from typing_extensions import Annotated
import operator

class AgentState(TypedDict):
    """Agent状态类，在节点间传递"""

    # 输入
    user_query: str                      # 用户原始查询
    session_id: Optional[str]            # 会话ID
    chat_history: List[Dict[str, str]]   # 对话历史

    # 意图理解
    intent: str                          # 意图类型（search/analyze/compare/calculate等）
    query_type: str                      # 查询类型（simple/complex/multi_step）
    entities: List[Dict[str, Any]]       # 提取的实体
    rewritten_query: str                 # 重写后的查询

    # 检索相关
    retrieval_strategy: str              # 检索策略（vector/hybrid/table/adaptive）
    retrieved_docs: List[Dict[str, Any]] # 检索到的文档
    retrieval_scores: List[float]        # 检索分数
    retrieval_quality: float             # 检索质量评分（0-1）

    # 推理和分析
    reasoning_steps: List[str]           # 推理步骤
    analysis_results: Dict[str, Any]     # 分析结果
    table_results: List[Dict[str, Any]]  # 表格查询结果

    # 生成相关
    draft_answer: str                    # 草稿答案
    final_answer: str                    # 最终答案
    answer_quality: float                # 答案质量评分（0-1）

    # 元数据
    sources: List[Dict[str, Any]]        # 数据来源
    confidence: float                    # 整体置信度
    metadata: Dict[str, Any]             # 额外元数据

    # 控制标志
    should_reretrieve: bool              # 是否需要重新检索
    should_regenerate: bool              # 是否需要重新生成
    max_iterations: int                  # 最大迭代次数
    current_iteration: int               # 当前迭代次数
```

## Agent节点定义

### 1. MasterAgent（主控智能体）
- **职责**：工作流编排、决策控制
- **功能**：
  - 接收用户查询
  - 初始化状态
  - 协调各Agent
  - 控制流程分支

### 2. IntentAgent（意图识别智能体）
- **职责**：理解用户意图
- **输入**：user_query, chat_history
- **输出**：intent, query_type, entities, rewritten_query
- **功能**：
  - 意图分类（查询/分析/对比/计算等）
  - 实体提取（套餐名称、费用类型等）
  - 查询重写和优化
  - 查询复杂度评估

### 3. PlanAgent（规划智能体）
- **职责**：制定检索策略
- **输入**：intent, query_type, entities
- **输出**：retrieval_strategy
- **功能**：
  - 根据意图选择检索策略
  - 决定使用哪些工具
  - 规划检索顺序

### 4. RetrievalAgent（检索智能体）
- **职责**：执行多源检索
- **输入**：rewritten_query, retrieval_strategy
- **输出**：retrieved_docs, retrieval_scores, table_results
- **功能**：
  - 向量检索
  - 混合检索（向量+BM25）
  - 表格数据检索
  - 结果融合和排序

### 5. EvaluateRetrievalNode（检索评估节点）
- **职责**：评估检索质量（Self-RAG）
- **输入**：retrieved_docs, user_query
- **输出**：retrieval_quality, should_reretrieve
- **功能**：
  - 计算检索质量分数
  - 判断是否需要重新检索
  - 决定是否调整查询

### 6. ReretrieveNode（重新检索节点）
- **职责**：执行重新检索
- **输入**：user_query, previous_docs
- **输出**：retrieved_docs (updated)
- **功能**：
  - 查询扩展
  - 调整检索参数
  - 执行新的检索

### 7. ReasoningAgent（推理智能体）
- **职责**：分析检索结果
- **输入**：retrieved_docs, table_results, intent
- **输出**：reasoning_steps, analysis_results
- **功能**：
  - 提取关键信息
  - 数据推理和计算
  - 多源信息关联
  - 生成推理链

### 8. GenerateAgent（生成智能体）
- **职责**：生成答案
- **输入**：reasoning_steps, analysis_results, user_query
- **输出**：draft_answer
- **功能**：
  - 基于上下文生成答案
  - 引用数据来源
  - 格式化输出

### 9. ReflectAgent（反思智能体）
- **职责**：自我评估答案质量
- **输入**：draft_answer, user_query, retrieved_docs
- **输出**：answer_quality, should_regenerate
- **功能**：
  - 评估答案相关性
  - 检查事实准确性
  - 判断是否需要重新生成

### 10. RegenerateNode（重新生成节点）
- **职责**：重新生成答案
- **输入**：feedback, previous_context
- **输出**：draft_answer (updated)
- **功能**：
  - 基于反馈调整生成
  - 优化答案结构

### 11. SynthesisAgent（综合智能体）
- **职责**：最终答案综合
- **输入**：draft_answer, reasoning_steps, sources
- **输出**：final_answer, confidence, sources
- **功能**：
  - 整合所有信息
  - 生成结构化答案
  - 计算置信度
  - 准备来源引用

## 条件边（Conditional Edges）

### 1. 检索策略分支
```python
def decide_retrieval_strategy(state: AgentState) -> str:
    """根据意图决定检索策略"""
    if state["intent"] == "table_query":
        return "table_retrieval"
    elif state["query_type"] == "complex":
        return "hybrid_retrieval"
    else:
        return "vector_retrieval"
```

### 2. 检索质量分支（Self-RAG）
```python
def should_reretrieve(state: AgentState) -> str:
    """判断是否需要重新检索"""
    if state["retrieval_quality"] < 0.6 and state["current_iteration"] < state["max_iterations"]:
        return "reretrieve"
    else:
        return "continue_to_reasoning"
```

### 3. 答案质量分支（Self-RAG）
```python
def should_regenerate(state: AgentState) -> str:
    """判断是否需要重新生成"""
    if state["answer_quality"] < 0.7 and state["current_iteration"] < state["max_iterations"]:
        return "regenerate"
    else:
        return "finalize"
```

## 工作流程

### 简单查询流程
```
用户查询 → 意图识别 → 规划 → 向量检索 → [评估] → 推理 → 生成 → [评估] → 综合 → 返回
```

### 复杂查询流程（带Self-RAG）
```
用户查询 → 意图识别 → 规划 → 混合检索 → [评估↓] → 推理 → 生成 → [评估↓] → 综合 → 返回
                                        ↓                    ↓
                                    质量不足              质量不足
                                        ↓                    ↓
                                    查询扩展               重新生成
                                        ↓                    ↓
                                    重新检索 ────────────────┘
```

### 多步骤推理流程
```
用户查询 → 意图识别（多步骤） → 规划 → 检索1 → 推理1 → 检索2 → 推理2 → 综合 → 生成 → 返回
```

## API接口设计

### 1. 文档入库接口
**POST** `/api/documents/ingest`
```json
// 请求
{
  "file": <binary>
}

// 响应
{
  "success": true,
  "document_id": "uuid",
  "filename": "document.pdf",
  "chunks_count": 42,
  "tables_extracted": 3,
  "status": "indexed"
}
```

### 2. AI聊天接口（统一入口）
**POST** `/api/chat`
```json
// 请求
{
  "message": "59元套餐的分成比例是多少？",
  "session_id": "optional-session-id",
  "stream": false,
  "config": {
    "max_iterations": 3,
    "temperature": 0.7
  }
}

// 响应
{
  "success": true,
  "session_id": "session-uuid",
  "answer": "根据渠道政策文档，59元套餐的分成比例是...",
  "reasoning": ["识别意图：费用查询", "检索到3个相关文档", ...],
  "sources": [
    {
      "type": "table",
      "source": "费用标准表.xlsx",
      "confidence": 0.95
    }
  ],
  "confidence": 0.87,
  "metadata": {
    "intent": "fee_query",
    "iterations": 1,
    "retrieval_strategy": "hybrid"
  }
}
```

### 3. 流式聊天接口（可选）
**POST** `/api/chat/stream`
- Server-Sent Events (SSE)
- 实时返回Agent思考过程
- 流式输出答案

## 文件结构

```
backend/
├── langgraph_agents/
│   ├── __init__.py
│   ├── state.py                    # AgentState定义
│   ├── master_graph.py             # LangGraph工作流图
│   ├── nodes/                      # Agent节点
│   │   ├── __init__.py
│   │   ├── intent_agent.py         # 意图识别
│   │   ├── plan_agent.py           # 规划
│   │   ├── retrieval_agent.py      # 检索
│   │   ├── reasoning_agent.py      # 推理
│   │   ├── generate_agent.py       # 生成
│   │   ├── reflect_agent.py        # 反思
│   │   └── synthesis_agent.py      # 综合
│   ├── edges/                      # 条件边
│   │   ├── __init__.py
│   │   └── conditional_edges.py
│   └── tools/                      # 工具函数
│       ├── __init__.py
│       ├── retrievers.py
│       ├── analyzers.py
│       └── evaluators.py
├── services/
│   ├── chat_service.py             # 聊天服务（新）
│   ├── document_service.py         # 文档服务（新）
│   └── ... (现有服务)
├── routes/
│   ├── chat_routes.py              # 聊天路由（新）
│   └── document_routes.py          # 文档路由（新）
└── main.py                          # 主应用（更新）
```

## 依赖更新

```txt
# 新增依赖
langgraph>=0.2.0
langchain>=0.3.0
langchain-core>=0.3.0
langchain-ollama>=0.2.0
```

## 优势

1. **统一入口**：所有AI交互通过 `/api/chat`
2. **智能路由**：自动识别意图并调用合适的Agent
3. **自我优化**：Self-RAG机制自动提升质量
4. **可扩展性**：轻松添加新Agent和工具
5. **可视化**：LangGraph提供状态机可视化
6. **流式输出**：支持实时返回思考过程
7. **会话管理**：内置上下文记忆
8. **性能监控**：集成LangSmith追踪

## 迁移策略

1. **Phase 1**：搭建LangGraph框架和基础节点
2. **Phase 2**：实现核心Agent（Intent, Retrieval, Reasoning, Generate）
3. **Phase 3**：添加Self-RAG机制（Reflect, Reretrieve）
4. **Phase 4**：优化和测试
5. **Phase 5**：前端集成

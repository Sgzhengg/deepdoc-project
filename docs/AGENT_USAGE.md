# Agentic RAG 系统使用说明

## 概述

Agentic RAG 系统是专门针对运营商渠道业务设计的智能问答系统，结合了：
- **查询理解**：理解用户查询意图，提取关键实体
- **表格分析**：智能解析渠道政策表格数据
- **向量检索**：基于语义相似度的文档检索

## 新增功能

### 1. 查询理解模块 (`agents/query_understanding.py`)

**功能：**
- 意图识别：政策查询、费用计算、佣金查询、产品信息、规则说明、对比分析、资格检查
- 实体提取：金额、套餐档次、费用类型、业务场景、渠道类型
- 查询重写：生成多个查询变体以提高召回率
- 过滤条件生成：基于实体生成结构化过滤条件

**支持的实体类型：**
```python
- amount: 金额（如：59元、100元）
- tier: 套餐档次（低档、中低档、中高档、高档）
- fee_type: 费用类型（实名手续费、充值手续费、套餐分成、阶段激励）
- scenario: 业务场景（新增、存量、校园、政企）
- channel: 渠道类型（社会渠道、自营厅、校园渠道、线上渠道）
```

### 2. 增强的表格分析器 (`agents/enhanced_table_analyzer.py`)

**功能：**
- 从 Word/Excel 文档加载表格
- 表格类型识别：费用标准表、产品列表表、对比表、矩阵表
- 自然语言查询表格
- 布尔标记识别（√/X）

**支持的查询类型：**
```python
- fee_query: 费用查询（"59元套餐多少钱？"）
- applicability: 适用性查询（"哪些套餐适用？"）
- product_lookup: 产品查询（"产品ID是多少？"）
- comparison: 对比查询（"有什么差异？"）
- general: 通用查询
```

### 3. 渠道政策智能体 (`agents/channel_policy_agent.py`)

**功能：**
- 综合查询理解、表格分析、向量检索
- 多源信息融合
- 智能答案生成
- 推理过程追踪

**工作流程：**
```
1. 理解查询 → 意图识别、实体提取
2. 执行检索 → 表格数据 + 向量检索
3. 综合分析 → 根据意图生成答案
4. 返回结果 → 答案 + 来源 + 推理过程
```

## API 端点

### 加载文档
```http
POST /agent/load-document?file_path=C:/Users/Administrator/Desktop/12月渠道政策/12月放号独立部分-酬金.docx
```

**响应示例：**
```json
{
  "status": "success",
  "message": "成功加载文档",
  "tables_count": 17,
  "tables": [
    {
      "index": 0,
      "type": "fee_schedule",
      "rows": 10,
      "cols": 7,
      "headers": ["业务类型", "费用标准", "59元以下套餐", ...]
    }
  ]
}
```

### 智能问答
```http
POST /agent/query?query=59元套餐的分成是多少？&top_k=10
```

**响应示例：**
```json
{
  "status": "success",
  "query": "59元套餐的分成是多少？",
  "answer": "💰 费用信息:\n行2: 实收套餐分成激励（高价值激励积分） | 实收套餐费50%/40%*6个月 | √ | √ | √ | √ | SH2000001",
  "confidence": 0.85,
  "sources": [
    {
      "type": "table",
      "table_index": 0,
      "confidence": 0.9
    }
  ],
  "reasoning": [
    "步骤1: 分析查询意图和实体",
    "  - 意图: product_info",
    "  - 实体: 2个",
    "步骤2: 执行多源检索",
    "  2.1 检索表格数据...",
    "       找到 1 个表格结果"
  ],
  "metadata": {
    "intent": "product_info",
    "query_type": "simple",
    "entities": [
      {"type": "amount", "value": "59"},
      {"type": "fee_type", "value": "套餐分成"}
    ]
  }
}
```

### 查询理解分析
```http
GET /agent/query/understand?query=129元套餐的充值激励是多少？
```

**响应示例：**
```json
{
  "status": "success",
  "original_query": "129元套餐的充值激励是多少？",
  "intent": "fee_calculation",
  "query_type": "simple",
  "entities": [
    {"type": "amount", "value": "129", "confidence": 0.9},
    {"type": "tier", "value": "高档", "confidence": 0.85},
    {"type": "fee_type", "value": "充值激励", "confidence": 0.9}
  ],
  "rewritten_queries": [
    "129元套餐的充值激励是多少？",
    "高档套餐 充值激励 费用标准 分成规则"
  ],
  "filters": {
    "tier": "高档",
    "fee_type": "充值激励"
  }
}
```

### 表格查询
```http
POST /agent/table/query?query=实名手续费的费用编码
```

### 列出所有表格
```http
GET /agent/tables
```

## 测试方法

### 方法1：使用测试脚本
```bash
cd Z:\deepdoc-project\backend
venv\Scripts\python.exe test_agent_system.py
```

### 方法2：通过 API 测试
```bash
# 1. 启动服务
cd Z:\deepdoc-project\backend
python main.py

# 2. 加载文档
curl -X POST "http://localhost:8000/agent/load-document?file_path=C:/Users/Administrator/Desktop/12月渠道政策/12月放号独立部分-酬金.docx"

# 3. 智能问答
curl -X POST "http://localhost:8000/agent/query?query=59元套餐的分成是多少？"
```

### 方法3：使用 Swagger UI
```
http://localhost:8000/docs
```

找到 "Agentic RAG" 标签下的端点进行交互式测试。

## 示例查询

| 查询类型 | 示例 |
|----------|------|
| 费用查询 | "59元套餐的分成是多少？" |
| 规则说明 | "实名手续费怎么计算？" |
| 适用性查询 | "129元以上套餐适用哪些费用？" |
| 条件查询 | "充值考核的要求是什么？" |
| 对比查询 | "59元和99元套餐的费用有什么区别？" |
| 产品查询 | "充值激励的费用编码是什么？" |

## 系统架构

```
请求
  ↓
查询理解 (意图识别 + 实体提取)
  ↓
┌─────────────┬─────────────┐
│             │             │
表格分析器    向量检索器   过滤器
│             │             │
└─────────────┴─────────────┘
  ↓
答案综合生成
  ↓
响应 (答案 + 来源 + 推理过程)
```

## 扩展建议

### 1. 添加更多实体类型
在 `query_understanding.py` 中扩展实体提取规则

### 2. 优化表格识别
在 `enhanced_table_analyzer.py` 中添加更多表格类型模式

### 3. 增强答案生成
在 `channel_policy_agent.py` 中为不同意图添加专门的答案生成逻辑

### 4. 集成 LLM
可以集成 OpenAI/本地 LLM 来提升答案质量

## 性能优化

- 表格数据缓存在内存中
- 向量检索使用 Qdrant 高性能搜索
- 查询理解使用快速正则匹配
- 支持批量查询和异步处理

## 故障排查

### 问题1：智能体未初始化
**解决方案：** 确保先调用 `/agent/load-document` 加载文档

### 问题2：表格查询返回空结果
**解决方案：** 检查文档是否包含表格，使用 `/agent/tables` 确认

### 问题3：中文显示乱码
**解决方案：** 终端编码问题，不影响功能，使用 API 或 Swagger UI 测试

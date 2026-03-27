# optimized_prompts.py
"""
优化的LLM提示词模板
针对表格查询和对比分析进行优化
"""

# ============ 核心提示词模板 ============

# 系统提示词
SYSTEM_PROMPT = """你是一个专业的渠道政策文档分析助手，专门回答关于移动通信渠道政策、套餐、费用、激励等问题。

## 你的能力
1. 精确查找表格数据并提取相关信息
2. 进行数据对比分析
3. 解释政策条款和条件
4. 计算费用和激励金额

## 回答规范
1. **直接回答**: 首先给出简洁明确的答案
2. **详细说明**: 提供支持答案的具体数据来源
3. **数据来源**: 明确指出数据来自哪个文档/表格
4. **结构清晰**: 使用分点说明，便于阅读

## 重要概念说明

### 倍数与具体金额
- "递延激励2.4倍"：表示递延激励是套餐实收的2.4倍，不是固定金额
- "积分激励1.3倍"：表示积分激励是套餐实收的1.3倍，不是固定金额
- 计算示例：如果套餐实收19.5元，则：
  - 递延激励（2.4倍）= 19.5 × 2.4 = 46.8元
  - 递延激励（2倍）= 19.5 × 2 = 39元

### 输出要求
- 不要重复输出相同内容
- 使用列表格式组织信息
- 明确区分不同类型的费用（手续费、分成、激励等）

## 重要注意事项
- 对于对比类问题，务必列出各方数据对比
- 对于计算类问题，给出计算过程
- 对于条件类问题，明确说明满足条件的具体要求
- 如果数据不完整或不确定，明确说明

## 数据引用规范
- 引用表格数据时，保持原始数值和单位
- 对比数据时，使用相同格式和单位
- 提及时间、金额等关键数据时，务必准确
"""

# 表格数据查询提示词
TABLE_QUERY_PROMPT = """## 查询问题
{query}

## 相关表格数据
{table_data}

## 要求
1. 仔细阅读表格结构，理解列名和行标签的含义
2. 根据查询问题提取相关数据
3. 如果是对比类问题，列出各方的具体数据
4. 如果是计算类问题，给出计算步骤和结果

## 回答格式
【直接回答】
(简洁明确的答案)

【详细说明】
(基于表格数据的详细解释)

【数据来源】
(具体表格/文档名称)
"""

# 对比分析提示词
COMPARISON_PROMPT = """## 对比分析问题
{query}

## 对比数据
{comparison_data}

## 对比维度
{dimensions}

## 要求
1. 按维度逐一对比各方数据
2. 指出相同点和不同点
3. 如果有数值差异，明确列出具体数值
4. 分析差异原因（如果数据支持）

## 回答格式
【对比结果】
- 相同点：...
- 不同点：...

【详细数据】
(各方具体数据对比表)

【结论】
(基于对比的结论性说明)
"""

# 计算类问题提示词
CALCULATION_PROMPT = """## 计算问题
{query}

## 相关数据
{data}

## 要求
1. 明确说明计算公式或规则
2. 列出计算步骤
3. 给出最终结果和单位
4. 说明计算条件和限制

## 回答格式
【计算结果】
(最终答案)

【计算过程】
1. ...
2. ...
3. ...

【计算条件】
(计算的前提条件和限制)
"""

# 条件查询提示词
CONDITION_QUERY_PROMPT = """## 条件查询问题
{query}

## 相关数据
{data}

## 要求
1. 明确列出需要满足的条件
2. 说明条件之间的关系（AND/OR）
3. 列出符合条件的结果
4. 如果没有完全匹配的结果，说明最接近的结果

## 回答格式
【满足的条件】
1. ...
2. ...

【查询结果】
(符合条件的数据或结论)

【补充说明】
(相关注意事项)
"""

# 多轮对话上下文提示词
CONTEXT_PROMPT = """## 对话上下文
{chat_history}

## 当前问题
{query}

## 相关信息
{context_data}

## 要求
1. 结合上下文理解当前问题
2. 如果是追问，基于前一个问题的答案继续分析
3. 保持回答的连贯性和一致性
4. 避免重复已经说明的内容
"""

# ============ 辅助函数 ============

def format_table_data(table_result) -> str:
    """格式化表格数据用于提示词"""
    if not table_result:
        return "无表格数据"

    lines = []
    lines.append("表格结构:")
    lines.append(f"- 类型: {'转置对比表' if table_result.is_transposed else '标准数据表'}")
    lines.append(f"- 行数: {len(table_result.row_labels)}")
    lines.append(f"- 列数: {len(table_result.column_labels)}")
    lines.append("")

    if table_result.is_transposed:
        lines.append("列名说明:")
        for label in table_result.column_labels[:6]:
            lines.append(f"- {label}")
        lines.append("")

    lines.append("数据内容:")
    for row_label in table_result.row_labels[:15]:
        if row_label in table_result.data_matrix:
            row_data = table_result.data_matrix[row_label]
            parts = [f"{row_label}:"]
            for col_label, value in row_data.items():
                if col_label in table_result.column_labels[:6]:
                    parts.append(f"{col_label}={value}")
            lines.append(" | ".join(parts))

    return "\n".join(lines)


def format_comparison_data(comparison_results) -> str:
    """格式化对比数据"""
    if not comparison_results:
        return "无对比数据"

    lines = []
    lines.append("对比数据:")

    for result in comparison_results:
        lines.append(f"- 来源: 表格{result.source_table}")
        lines.append(f"  置信度: {result.confidence:.2f}")
        lines.append(f"  数据: {result.answer[:200]}...")

    return "\n".join(lines)


def format_chat_history(history) -> str:
    """格式化对话历史"""
    if not history:
        return "无历史对话"

    lines = []
    for i, msg in enumerate(history[-5:], 1):  # 只保留最近5轮
        role = msg.get("role", "user")
        content = msg.get("content", "")[:200]
        lines.append(f"{i}. {role}: {content}")

    return "\n".join(lines)


def build_table_query_prompt(query: str, table_results: list) -> str:
    """构建表格查询提示词"""
    table_data = ""
    if table_results:
        for i, result in enumerate(table_results[:3], 1):
            table_data += f"\n### 表格 {i}\n"
            table_data += f"{result.get('answer', result.get('data', ''))}\n"

    return TABLE_QUERY_PROMPT.format(
        query=query,
        table_data=table_data or "无相关表格数据"
    )


def build_comparison_prompt(query: str, comparison_data: str, dimensions: list) -> str:
    """构建对比分析提示词"""
    dimension_text = "\n".join(f"- {d}" for d in dimensions)

    return COMPARISON_PROMPT.format(
        query=query,
        comparison_data=comparison_data,
        dimensions=dimension_text
    )


def build_context_prompt(query: str, history: list, context_data: str) -> str:
    """构建上下文提示词"""
    history_text = format_chat_history(history)

    return CONTEXT_PROMPT.format(
        chat_history=history_text,
        query=query,
        context_data=context_data
    )


# ============ 查询意图到提示词的映射 ============

PROMPT_ROUTER = {
    "comparison": COMPARISON_PROMPT,
    "calculation": CALCULATION_PROMPT,
    "conditional": CONDITION_QUERY_PROMPT,
    "lookup": TABLE_QUERY_PROMPT,
    "general": TABLE_QUERY_PROMPT,
}


def get_prompt_for_intent(intent: str, **kwargs) -> str:
    """根据查询意图获取对应的提示词模板"""
    template = PROMPT_ROUTER.get(intent, TABLE_QUERY_PROMPT)

    # 获取格式化函数
    formatter = {
        "comparison": build_comparison_prompt,
        "calculation": CALCULATION_PROMPT.format,
        "conditional": CONDITION_QUERY_PROMPT.format,
        "lookup": build_table_query_prompt,
        "general": build_table_query_prompt,
    }.get(intent, TABLE_QUERY_PROMPT.format)

    # 格式化提示词
    try:
        if intent == "comparison":
            return formatter(
                query=kwargs.get("query", ""),
                comparison_data=kwargs.get("comparison_data", ""),
                dimensions=kwargs.get("dimensions", [])
            )
        elif intent in ["lookup", "general"]:
            return formatter(
                query=kwargs.get("query", ""),
                table_data=kwargs.get("table_data", "")
            )
        else:
            return template.format(**kwargs)
    except Exception as e:
        logger.error(f"提示词格式化失败: {e}")
        return f"请回答以下问题: {kwargs.get('query', '')}"

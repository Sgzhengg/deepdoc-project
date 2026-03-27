"""
IntentAgent - 意图识别智能体
负责理解用户查询意图、提取实体、重写查询

设计原则：
- 不使用硬编码的业务术语，保持泛化能力
- 依赖 LLM 进行上下文理解和查询重写
- 最小化规则，最大化 LLM 的理解能力
"""

import logging
import json
from typing import Dict, Any, Optional
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import AgentState

logger = logging.getLogger(__name__)


class IntentAgent:
    """
    意图识别Agent

    功能：
    1. 意图分类：识别用户想做什么（查询/分析/对比/计算等）
    2. 查询重写：基于对话历史优化用户查询
    3. 实体提取：提取关键实体（由 LLM 完成）

    设计原则：
    - 无硬编码业务术语
    - 依赖 LLM 理解能力
    - 保持系统泛化能力
    """

    # 通用的意图类型定义（不绑定具体业务）
    INTENTS = {
        "search": "文档搜索 - 搜索相关文档和信息",
        "table_query": "表格查询 - 查询表格数据",
        "analyze": "文档分析 - 分析文档内容",
        "compare": "对比分析 - 对比多个选项",
        "calculate": "计算 - 执行费用或数据计算",
        "status": "状态查询 - 查询知识库或系统状态",
        "general": "通用问答 - 一般性问题"
    }

    QUERY_TYPES = {
        "simple": "简单查询 - 单一意图，直接检索",
        "complex": "复杂查询 - 多步骤，需要推理",
        "multi_step": "多步骤查询 - 需要多次检索和推理"
    }

    def __init__(self, llm: ChatOllama = None):
        """
        初始化IntentAgent

        Args:
            llm: LLM实例（用于意图识别和查询重写）
        """
        self.llm = llm
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """构建系统提示词（简化版，发挥deepseek-r1:32B能力）"""
        return """分析用户查询意图，返回JSON格式：

```json
{
  "intent": "search|table_query|analyze|compare|calculate|status|general",
  "query_type": "simple|complex|multi_step",
  "rewritten_query": "重写后的查询（追问时结合上下文补全为独立问题）",
  "reasoning": "简短说明"
}
```

意图说明：
- search: 文档搜索
- table_query: 表格数据查询
- analyze: 分析总结
- compare: 对比差异
- calculate: 数值计算
- status: 系统状态查询
- general: 其他问题

查询类型：
- simple: 单一问题
- complex: 需要多步推理
- multi_step: 需要多次检索

追问处理：将代词（它、这个、那个）和省略句补全为包含上下文的完整问题。
"""

    async def __call__(self, state: AgentState) -> AgentState:
        """
        执行意图识别

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        user_query = state["user_query"]
        chat_history = state.get("chat_history", [])
        logger.info(f"IntentAgent: 分析查询 - {user_query}")

        try:
            if self.llm:
                result = await self._llm_intent_analysis(user_query, chat_history)
            else:
                result = self._rule_intent_analysis(user_query)

            # 更新状态
            state["intent"] = result["intent"]
            state["query_type"] = result["query_type"]
            state["entities"] = result.get("entities", [])
            state["rewritten_query"] = result.get("rewritten_query", user_query)

            step = f"🔍 意图: {result['intent']}, 类型: {result['query_type']}"
            state["reasoning_steps"] = [step]

            logger.info(f"IntentAgent: 意图={result['intent']}, 类型={result['query_type']}")

        except Exception as e:
            logger.error(f"IntentAgent错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 降级为默认值
            state["intent"] = "general"
            state["query_type"] = "simple"
            state["rewritten_query"] = user_query
            state["entities"] = []

        return state

    def _expand_query(self, query: str) -> str:
        """
        查询扩展：将模糊查询扩展为更完整的查询

        设计原则：
        - 使用通用模式匹配，不硬编码业务术语
        - 保持泛化能力，适用于各种领域

        Args:
            query: 原始查询

        Returns:
            扩展后的查询（如果需要），否则返回原查询
        """
        import re

        # 模式1: "XX资费是多少" -> "XX语音资费和XX流量资费分别是多少"
        pattern1 = r'(.{0,10})资费(.{0,5})'
        match1 = re.search(pattern1, query)
        if match1:
            prefix = match1.group(1)
            suffix = match1.group(2)
            if not any(word in query for word in ["和", "及", "分别", "与"]):
                common_prefixes = ["套外", "套餐", "国内", "国际", "漫游", "流量"]
                if any(p in prefix for p in common_prefixes):
                    expanded = f"{prefix}语音资费和{prefix}流量资费{suffix}"
                    logger.info(f"🔄 查询扩展: '{query}' -> '{expanded}'")
                    return expanded

        # 模式2: "有哪些XX" -> 添加"请详细列出所有类型"
        pattern2 = r'有哪些(.{0,8})(?:吗？|吗|？)?'
        match2 = re.search(pattern2, query)
        if match2:
            noun = match2.group(1)
            business_nouns = ["优惠", "福利", "活动", "权益", "服务", "业务", "产品", "套餐"]
            if any(bn in noun for bn in business_nouns):
                if "详细" not in query and "所有" not in query and "完整" not in query:
                    expanded = query.replace(f"有哪些{noun}", f"有哪些{noun}，请详细列出所有类型和具体内容")
                    logger.info(f"🔄 查询扩展: '{query}' -> '{expanded}'")
                    return expanded

        # 模式3: 涉及"满足XX条件" -> 添加"请详细说明所有相关条件"
        pattern3 = r'(满足|需要)(.{0,10})(条件|要求)'
        match3 = re.search(pattern3, query)
        if match3 and "详细" not in query and "所有" not in query:
            expanded = query + "，请详细说明所有相关条件"
            logger.info(f"🔄 查询扩展: '{query}' -> '{expanded}'")
            return expanded

        # 模式4: 对比类问题 - 确保"分别"出现
        if any(word in query for word in ["对比", "区别", "差异", "不同"]):
            if "分别" not in query and "各自" not in query:
                if query.endswith("？") or query.endswith("?"):
                    expanded = query[:-1] + "分别是多少？"
                    logger.info(f"🔄 查询扩展: '{query}' -> '{expanded}'")
                    return expanded
                elif query.endswith("是多少") or query.endswith("是"):
                    expanded = query + "分别是"
                    logger.info(f"🔄 查询扩展: '{query}' -> '{expanded}'")
                    return expanded

        return query

    async def _llm_intent_analysis(self, query: str, chat_history: list) -> Dict[str, Any]:
        """
        使用LLM进行意图分析和查询重写

        Args:
            query: 用户查询
            chat_history: 对话历史

        Returns:
            分析结果字典
        """
        # 先进行查询扩展
        expanded_query = self._expand_query(query)

        messages = [
            SystemMessage(content=self.system_prompt)
        ]

        # 使用扩展后的查询进行分析
        query_to_analyze = expanded_query

        # 构建用户消息
        if chat_history and len(chat_history) > 0:
            # 有对话历史，需要上下文理解
            history_text = self._format_chat_history(chat_history)
            user_prompt = f"""## 对话历史：
{history_text}

## 当前用户查询：
{query_to_analyze}

请分析当前查询的意图，并根据对话历史将查询重写为完整、独立的问题（如果需要）。"""
        else:
            # 无对话历史，直接分析
            user_prompt = f"## 用户查询：\n{query_to_analyze}\n\n请分析查询意图。"

        messages.append(HumanMessage(content=user_prompt))

        # 调用LLM
        response = await self.llm.ainvoke(messages)

        # 解析JSON响应
        content = response.content.strip()

        # 首先尝试直接解析
        try:
            result = json.loads(content)
            if "rewritten_query" not in result:
                # 如果LLM没有重写，使用扩展后的查询
                result["rewritten_query"] = expanded_query if expanded_query != query else query
            # 如果LLM重写了查询，检查是否需要进一步扩展
            elif result.get("rewritten_query") == query and expanded_query != query:
                result["rewritten_query"] = expanded_query
            return result
        except json.JSONDecodeError:
            pass

        # 尝试移除markdown代码块标记
        import re
        # 匹配 ```json ... ``` 或 ``` ... ```
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if code_block_match:
            try:
                result = json.loads(code_block_match.group(1))
                if "rewritten_query" not in result:
                    result["rewritten_query"] = expanded_query if expanded_query != query else query
                elif result.get("rewritten_query") == query and expanded_query != query:
                    result["rewritten_query"] = expanded_query
                return result
            except:
                pass

        # 尝试找到完整的JSON对象（支持嵌套）
        json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}', content, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                if "rewritten_query" not in result:
                    result["rewritten_query"] = expanded_query if expanded_query != query else query
                elif result.get("rewritten_query") == query and expanded_query != query:
                    result["rewritten_query"] = expanded_query
                return result
            except:
                pass

        # 所有方法都失败，记录警告并使用规则分析
        logger.warning(f"LLM返回的JSON解析失败，原始响应: {content[:300]}")
        fallback_result = self._rule_intent_analysis(expanded_query)
        # 确保返回扩展后的查询
        if fallback_result.get("rewritten_query") == query and expanded_query != query:
            fallback_result["rewritten_query"] = expanded_query
        return fallback_result

    def _format_chat_history(self, chat_history: list) -> str:
        """
        格式化对话历史

        优先展示最近的对话，适当压缩内容
        """
        if not chat_history:
            return ""

        # 取最近6轮对话
        recent_history = chat_history[-12:]

        formatted_lines = []
        for i, msg in enumerate(recent_history):
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # 压缩过长的消息（保留重要信息）
            if len(content) > 200:
                # 保留开头和结尾
                content = content[:100] + "..." + content[-50:]

            role_display = "用户" if role == "user" else "助手"
            formatted_lines.append(f"{role_display}: {content}")

        return "\n".join(formatted_lines)

    def _rule_intent_analysis(self, query: str) -> Dict[str, Any]:
        """
        基于规则的意图分析（后备方案，无硬编码）

        Args:
            query: 用户查询

        Returns:
            分析结果字典
        """
        # 通用意图识别规则（不绑定具体业务）
        intent = "general"

        if any(word in query for word in ["表格", "表单", "excel", "xlsx"]):
            intent = "table_query"
        elif any(word in query for word in ["搜索", "查找", "找", "文档"]):
            intent = "search"
        elif any(word in query for word in ["对比", "差异", "区别", "不同"]):
            intent = "compare"
        elif any(word in query for word in ["分析", "总结", "概括"]):
            intent = "analyze"
        elif any(word in query for word in ["计算", "总额", "总计"]):
            intent = "calculate"
        elif any(word in query for word in ["状态", "情况", "多少个", "几个"]):
            intent = "status"

        # 查询类型判断
        query_type = "simple"
        if "对比" in query or "和" in query or "分别" in query:
            query_type = "complex"
        elif "然后" in query or "接着" in query or "再" in query:
            query_type = "multi_step"
        elif any(word in query for word in ["为什么", "如何", "怎么", "原因"]):
            query_type = "complex"

        return {
            "intent": intent,
            "query_type": query_type,
            "entities": [],
            "rewritten_query": query,
            "reasoning": "基于规则的分析"
        }


def create_intent_agent(llm: ChatOllama = None) -> IntentAgent:
    """
    创建IntentAgent实例的工厂函数

    Args:
        llm: LLM实例

    Returns:
        IntentAgent实例
    """
    return IntentAgent(llm=llm)

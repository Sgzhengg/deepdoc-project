"""
ReasoningAgent - 推理智能体
负责分析检索结果、提取关键信息、执行推理
"""

import logging
from typing import Dict, Any, List
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from ..state import AgentState
from ..tools.calculation_tool import get_calculation_tool

logger = logging.getLogger(__name__)


class ReasoningAgent:
    """
    推理Agent

    功能：
    1. 信息提取：从检索结果中提取关键信息
    2. 数据推理：执行计算和逻辑推理
    3. 多源关联：关联不同来源的信息
    4. 生成推理链：构建清晰的推理过程
    """

    def __init__(self, llm: ChatOllama = None):
        """
        初始化ReasoningAgent

        Args:
            llm: LLM实例
        """
        self.llm = llm

    async def __call__(self, state: AgentState) -> AgentState:
        """
        执行推理分析

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        query = state["user_query"]
        intent = state["intent"]
        docs = state["retrieved_docs"]
        table_results = state.get("table_results", [])

        logger.info(f"ReasoningAgent: 分析 {len(docs)} 个文档和 {len(table_results)} 个表格结果")

        try:
            # 根据意图选择推理策略
            if intent == "calculate":
                result = await self._calculate_reasoning(query, docs, table_results)
            elif intent == "compare":
                result = await self._compare_reasoning(query, docs, table_results)
            elif intent == "table_query":
                result = await self._table_reasoning(query, table_results)
            else:
                result = await self._general_reasoning(query, docs, table_results)

            # 更新状态
            state["analysis_results"] = result.get("analysis", {})

            # 使用 operator.add 时，只返回这个节点添加的新步骤
            state["reasoning_steps"] = [f"🧠 推理完成: {result.get('analysis', {}).get('type', 'general')}"]

            # 构建数据来源（修复：添加 filename 字段）
            sources = []
            for i, doc in enumerate(docs[:3]):
                # 获取文档名称（优先使用 filename，其次 source_document，最后使用 id）
                doc_name = (
                    doc.get("metadata", {}).get("filename") or
                    doc.get("source_document") or
                    doc.get("filename") or
                    f"文档{i+1}"
                )
                sources.append({
                    "id": doc.get("id", f"doc_{i}"),
                    "filename": doc_name,
                    "type": "document",
                    "content": doc.get("text", "")[:200] + "...",
                    "score": state["retrieved_scores"][i] if i < len(state["retrieved_scores"]) else 0.0
                })

            for tr in table_results[:2]:
                table_name = (
                    tr.get("metadata", {}).get("source_document") or
                    tr.get("source_document") or
                    tr.get("filename") or
                    f"表格{len(sources)+1}"
                )
                sources.append({
                    "id": f"table_{len(sources)}",
                    "filename": table_name,
                    "type": "table",
                    "content": tr.get("answer", "")[:200] + "...",
                    "confidence": tr.get("confidence", 0.0),
                    "source": tr.get("source_table", "")
                })

            state["sources"] = sources

        except Exception as e:
            logger.error(f"ReasoningAgent错误: {e}")
            state["reasoning_steps"] = [f"❌ 推理失败: {str(e)}"]
            state["analysis_results"] = {}

        return state

    async def _calculate_reasoning(
        self,
        query: str,
        docs: List[Dict],
        table_results: List[Dict]
    ) -> Dict[str, Any]:
        """
        计算类推理

        修复问题2：使用专门的计算工具确保精确计算，而不是依赖LLM
        """
        # ========== 修复问题2：使用精确计算工具 ==========
        calc_tool = get_calculation_tool()

        # 检测并执行计算
        calc_result = calc_tool.analyze_and_calculate(query, docs)

        steps = [
            "📐 识别计算需求",
        ]

        analysis = {
            "type": "calculation",
            "data_points": [],
            "calculation": "",
            "calculation_result": None
        }

        # 如果检测到计算
        if calc_result["has_calculation"]:
            steps.append("🔢 提取数值数据")

            # 从表格结果提取数据
            if table_results:
                for tr in table_results:
                    if tr.get("answer"):
                        analysis["data_points"].append(tr["answer"])
                        steps.append(f"  - 从表格提取: {tr['answer'][:100]}")

            # 从文档提取数据
            for doc in docs[:3]:
                text = doc.get("text", "")
                if any(char.isdigit() for char in text):
                    analysis["data_points"].append(text[:200])
                    steps.append(f"  - 从文档提取: {text[:100]}...")

            # 执行精确计算
            steps.append("➕ 执行精确计算")
            analysis["calculation"] = calc_result.get("explanation", "")
            analysis["calculation_result"] = calc_result.get("total")

            # 添加计算步骤
            for calc in calc_result.get("calculations", []):
                steps.append(f"  ✅ {calc['explanation']}")

            logger.info(f"🧮 计算结果: {calc_result.get('explanation', '')}")
        else:
            # 没有检测到计算表达式，使用文档中的数据
            steps.append("📄 从文档提取相关数值")

            # 从表格结果提取数据
            if table_results:
                for tr in table_results:
                    if tr.get("answer"):
                        analysis["data_points"].append(tr["answer"])
                        steps.append(f"  - 从表格提取: {tr['answer'][:100]}")

            # 从文档提取数据
            for doc in docs[:3]:
                text = doc.get("text", "")
                if any(char.isdigit() for char in text):
                    analysis["data_points"].append(text[:200])
                    steps.append(f"  - 从文档提取: {text[:100]}...")

        return {"analysis": analysis, "steps": steps}

    async def _compare_reasoning(
        self,
        query: str,
        docs: List[Dict],
        table_results: List[Dict]
    ) -> Dict[str, Any]:
        """对比类推理"""
        steps = [
            "⚖️ 识别对比对象",
            "📋 提取对比信息",
            "🔍 分析差异"
        ]

        analysis = {
            "type": "comparison",
            "items": [],
            "differences": []
        }

        # 提取对比项
        import re
        numbers = re.findall(r'\d+', query)
        if len(numbers) >= 2:
            analysis["items"] = numbers[:2]
            steps.append(f"  - 对比项: {numbers[0]} vs {numbers[1]}")

        # 从文档提取对比信息
        for doc in docs[:5]:
            text = doc.get("text", "")
            if "差异" in text or "不同" in text or "区别" in text:
                analysis["differences"].append(text[:200])
                steps.append(f"  - 找到差异说明")

        return {"analysis": analysis, "steps": steps}

    async def _table_reasoning(
        self,
        query: str,
        table_results: List[Dict]
    ) -> Dict[str, Any]:
        """表格推理"""
        steps = [
            "📊 查询表格数据",
            f"✅ 找到 {len(table_results)} 个相关结果"
        ]

        analysis = {
            "type": "table_query",
            "results": table_results
        }

        for i, tr in enumerate(table_results[:3]):
            steps.append(f"  {i+1}. {tr.get('answer', '')[:100]}")

        return {"analysis": analysis, "steps": steps}

    async def _general_reasoning(
        self,
        query: str,
        docs: List[Dict],
        table_results: List[Dict]
    ) -> Dict[str, Any]:
        """通用推理"""
        steps = [
            "📖 分析相关文档",
            f"📚 基于 {len(docs)} 个文档进行推理"
        ]

        analysis = {
            "type": "general",
            "key_points": []
        }

        # 提取关键点
        for doc in docs[:3]:
            text = doc.get("text", "")
            # 简单的关键点提取（取前150字符）
            if text:
                analysis["key_points"].append(text[:150])
                steps.append(f"  - 关键信息: {text[:100]}...")

        return {"analysis": analysis, "steps": steps}


def create_reasoning_agent(llm: ChatOllama = None) -> ReasoningAgent:
    """创建ReasoningAgent实例"""
    return ReasoningAgent(llm=llm)

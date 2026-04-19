"""
RetrievalAgent - 检索智能体
负责执行多源检索（向量、混合、表格）

增强功能：
- 自动检测是否需要表格检索
- 同时使用向量检索和表格检索
- 合并多种检索结果

[Karpathy Loop 接入] 使用 optimization_surface.py 的查询重写和表格检测
"""

import logging
import re
import sys
import os
from typing import Dict, Any, List, Tuple
from langchain_ollama import ChatOllama

from ..state import AgentState

logger = logging.getLogger(__name__)

# ============== Karpathy Loop: 接入优化表面 ==============
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from optimization_surface import (
        get_optimization_config,
        build_qdrant_payload,
        rewrite_query,
        QDRANT_CONFIG,
        LANGGRAPH_PROMPTS
    )
    OPTIMIZATION_SURFACE_AVAILABLE = True
    logger.info("✅ [Karpathy Loop] RetrievalAgent: optimization_surface.py 已加载")
except ImportError as e:
    OPTIMIZATION_SURFACE_AVAILABLE = False
    logger.warning(f"⚠️ [Karpathy Loop] RetrievalAgent: optimization_surface.py 未找到 - {e}")
# ==============================================================


class RetrievalAgent:
    """
    检索Agent

    功能：
    1. 向量检索：基于语义相似度的检索
    2. 混合检索：向量 + BM25关键词检索
    3. 表格检索：专门查询表格数据
    4. 智能融合：自动判断是否需要表格检索并合并结果

    设计原则：依赖LLM意图判断，避免硬编码业务术语
    """

    def __init__(
        self,
        hybrid_retriever=None,
        table_analyzer=None,
        llm: ChatOllama = None
    ):
        """
        初始化RetrievalAgent

        Args:
            hybrid_retriever: 混合检索器实例
            table_analyzer: 表格分析器实例
            llm: LLM实例
        """
        self.hybrid_retriever = hybrid_retriever
        self.table_analyzer = table_analyzer
        self.llm = llm

    async def __call__(self, state: AgentState) -> AgentState:
        """
        执行检索（优化：直接根据intent决定策略）

        [Karpathy Loop] 使用 optimization_surface.py 的查询重写功能

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        query = state["rewritten_query"] or state["user_query"]

        # ============== Karpathy Loop: 应用查询重写 ==============
        if OPTIMIZATION_SURFACE_AVAILABLE and query == state["user_query"]:
            # 如果 rewritten_query 与原查询相同，尝试使用优化表面的重写
            rewritten = rewrite_query(query)
            if rewritten != query:
                query = rewritten
                logger.info(f"🔄 [Karpathy Loop] 查询重写: {state['user_query'][:30]}... -> {query[:30]}...")
        # ==============================================================

        intent = state["intent"]

        # 优化：直接根据intent决定检索策略，无需plan_retrieval节点
        strategy = "auto"  # 简化：统一使用auto策略
        if intent == "table_query":
            strategy = "table"
        elif intent in ["search", "analyze"]:
            strategy = "hybrid"

        logger.info(f"RetrievalAgent: 检索查询 - {query}, 策略={strategy}, 意图={intent}")

        try:
            # 检测是否需要表格检索
            needs_table = self._needs_table_retrieval(query, intent)
            logger.info(f"RetrievalAgent: 检测需要表格检索={needs_table}")

            if strategy == "table":
                # 强制表格检索
                docs, scores = await self._table_retrieval(query, state)
            elif strategy == "hybrid":
                # 混合检索
                docs, scores = await self._hybrid_retrieval(query, state, include_table=needs_table)
            elif strategy == "vector":
                # 向量检索
                docs, scores = await self._vector_retrieval(query, state)
            else:
                # 自动策略：根据查询内容决定
                if needs_table:
                    # 同时使用向量和表格检索
                    docs, scores = await self._hybrid_retrieval(query, state, include_table=True)
                else:
                    # 仅向量检索
                    docs, scores = await self._vector_retrieval(query, state)

            # 更新状态
            state["retrieved_docs"] = docs
            state["retrieved_scores"] = scores

            # 计算检索质量
            quality = self._calculate_retrieval_quality(scores, docs)
            state["retrieval_quality"] = quality

            # 使用 operator.add 时，只返回这个节点添加的新步骤
            strategy_used = f"表格+向量" if needs_table else strategy
            state["reasoning_steps"] = [f"📊 检索策略={strategy_used}, 获得{len(docs)}个文档, 质量={quality:.2f}"]

        except Exception as e:
            logger.error(f"RetrievalAgent错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            state["retrieved_docs"] = []
            state["retrieval_scores"] = []
            state["retrieval_quality"] = 0.0

        return state

    def _needs_table_retrieval(self, query: str, intent: str) -> bool:
        """
        检测是否需要表格检索

        [Karpathy Loop] 使用 optimization_surface.py 中的表格检测逻辑

        Args:
            query: 用户查询
            intent: 意图类型

        Returns:
            是否需要表格检索
        """
        query_lower = query.lower()

        # 通用化检测：依赖LLM意图判断，不使用硬编码业务关键词
        # table_query意图已经由IntentAgent通过LLM识别
        if intent == "table_query":
            logger.info(f"  -> 意图是 table_query，需要表格检索")
            return True

        # ============== Karpathy Loop: 使用优化表面的表格检测 ==============
        if OPTIMIZATION_SURFACE_AVAILABLE:
            # 使用 build_qdrant_payload 中的表格检测逻辑
            payload = build_qdrant_payload(query, is_table_query=False)
            # 如果 payload 包含 filter 且 filter 包含 table 类型，说明是表格查询
            if "filter" in payload:
                logger.info(f"  -> [Karpathy Loop] build_qdrant_payload 检测到表格查询")
                return True

        # ============== 原逻辑（降级/补充） ==============
        # 通用模式：包含数字+符号的组合（可能是表格数据查询）
        match = re.search(r'\d+%|\d+[元C元]|[A-Z]\d+|T\d+', query_lower)
        if match:
            logger.info(f"  -> 检测到数字模式 '{match.group()}'，需要表格检索")
            return True
        # ==============================================================

        logger.info(f"  -> 不需要表格检索 (intent={intent}, query={query[:30]})")
        return False

    async def _vector_retrieval(
        self,
        query: str,
        state: AgentState
    ) -> Tuple[List[Dict], List[float]]:
        """向量检索"""
        try:
            if not self.hybrid_retriever:
                logger.warning("混合检索器未初始化")
                return [], []

            # 使用混合检索器的向量检索部分
            results = self.hybrid_retriever.hybrid_search(
                query=query,
                top_k=10,
                fusion_method="weighted",
                vector_weight=1.0,
                keyword_weight=0.0  # 纯向量检索
            )

            docs = [{"text": r.get("text", ""), "metadata": r.get("metadata", {})} for r in results]
            scores = [r.get("score", 0.0) for r in results]

            return docs, scores

        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return [], []

    async def _hybrid_retrieval(
        self,
        query: str,
        state: AgentState,
        include_table: bool = False
    ) -> Tuple[List[Dict], List[float]]:
        """
        混合检索（向量+关键词，可选表格）

        Args:
            query: 查询内容
            state: 状态
            include_table: 是否包含表格检索

        Returns:
            文档列表和分数列表
        """
        all_docs = []
        all_scores = []

        try:
            # 1. 向量+关键词混合检索（优化：增加检索数量）
            if self.hybrid_retriever:
                results = self.hybrid_retriever.hybrid_search(
                    query=query,
                    top_k=10,  # 优化：从20减少到10，提升检索速度
                    fusion_method="rrf"
                )

                for r in results:
                    all_docs.append({
                        "text": r.get("text", ""),
                        "metadata": r.get("metadata", {})
                    })
                    all_scores.append(r.get("fusion_score", r.get("score", 0.0)))

                logger.info(f"🔍 混合检索返回 {len(results)} 个结果")

        except Exception as e:
            logger.error(f"混合检索失败: {e}")

        # 2. 表格检索（如果需要）
        if include_table and self.table_analyzer:
            try:
                table_summary = self.table_analyzer.get_table_summary()
                logger.info(f"🔍 表格分析器状态: {len(table_summary)} 个表格")

                results = self.table_analyzer.query(query, filters=state.get("entities", []))
                logger.info(f"📊 表格查询返回 {len(results)} 个结果")

                # 打印每个表格结果
                for i, r in enumerate(results[:3]):
                    logger.info(f"   表格结果[{i}]: answer={r.answer[:100] if r.answer else 'None'}, source={r.source_table}")

                # 保存表格结果到状态
                state["table_results"] = [
                    {
                        "answer": r.answer,
                        "confidence": r.confidence,
                        "source_table": r.source_table,
                        "explanation": r.explanation
                    }
                    for r in results
                ]

                # 将表格结果添加到文档列表（权重较高）
                for r in results:
                    all_docs.insert(0, {  # 表格结果放在前面
                        "text": f"[表格数据] {r.answer}",
                        "metadata": {
                            "type": "table",
                            "source_table": r.source_table,
                            "explanation": r.explanation,
                            "confidence": r.confidence
                        }
                    })
                    all_scores.insert(0, r.confidence * 1.2)  # 表格结果加权

            except Exception as e:
                logger.error(f"表格检索失败: {e}")

        return all_docs, all_scores

    async def _table_retrieval(
        self,
        query: str,
        state: AgentState
    ) -> Tuple[List[Dict], List[float]]:
        """纯表格检索"""
        try:
            if not self.table_analyzer:
                logger.warning("表格分析器未初始化")
                return [], []

            table_summary = self.table_analyzer.get_table_summary()
            logger.info(f"🔍 表格分析器状态: {len(table_summary)} 个表格")

            results = self.table_analyzer.query(query, filters=state.get("entities", []))
            logger.info(f"📊 表格查询返回 {len(results)} 个结果")

            table_results = []
            scores = []

            for r in results:
                table_results.append({
                    "text": r.answer,
                    "metadata": {
                        "type": "table",
                        "source_table": r.source_table,
                        "explanation": r.explanation
                    }
                })
                scores.append(r.confidence)

            # 保存表格结果
            state["table_results"] = [
                {
                    "answer": r.answer,
                    "confidence": r.confidence,
                    "source_table": r.source_table,
                    "explanation": r.explanation
                }
                for r in results
            ]

            return table_results, scores

        except Exception as e:
            logger.error(f"表格检索失败: {e}")
            return [], []

    def _calculate_retrieval_quality(
        self,
        scores: List[float],
        docs: List[Dict]
    ) -> float:
        """
        计算检索质量

        Args:
            scores: 检索分数列表
            docs: 检索到的文档列表

        Returns:
            质量评分（0-1）
        """
        if not scores:
            return 0.0

        # 因素1: 平均分数
        avg_score = sum(scores) / len(scores)

        # 因素2: 文档数量
        doc_count_factor = min(len(docs) / 5.0, 1.0)

        # 因素3: 最高分
        max_score = max(scores) if scores else 0.0

        # 综合计算
        quality = (avg_score * 0.4 + doc_count_factor * 0.3 + max_score * 0.3)

        return min(quality, 1.0)


def create_retrieval_agent(
    hybrid_retriever=None,
    table_analyzer=None,
    llm: ChatOllama = None
) -> RetrievalAgent:
    """创建RetrievalAgent实例"""
    return RetrievalAgent(
        hybrid_retriever=hybrid_retriever,
        table_analyzer=table_analyzer,
        llm=llm
    )

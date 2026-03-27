# channel_policy_agent.py
"""
渠道政策分析智能体 - Agentic RAG 系统
结合查询理解、表格分析、向量检索的智能问答系统
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from agents.query_understanding import get_query_understander, QueryAnalysis, QueryIntent
from agents.enhanced_table_analyzer import get_table_analyzer, QueryResult
from hybrid_search import HybridRetriever

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
    """智能体响应"""
    answer: str
    sources: List[Dict[str, Any]]
    confidence: float
    reasoning: List[str]  # 推理过程
    metadata: Dict[str, Any]


class ChannelPolicyAgent:
    """
    渠道政策分析智能体

    工作流程：
    1. 理解查询（意图识别、实体提取）
    2. 制定检索策略
    3. 执行多源检索（向量数据库、表格数据）
    4. 综合分析结果
    5. 生成结构化回答
    """

    def __init__(self, vector_storage=None, embedding_service=None, hybrid_retriever=None):
        """
        初始化智能体

        Args:
            vector_storage: 向量存储
            embedding_service: 嵌入服务
            hybrid_retriever: 混合检索器
        """
        self.query_understander = get_query_understander()
        self.table_analyzer = get_table_analyzer()
        self.hybrid_retriever = hybrid_retriever

        self.vector_storage = vector_storage
        self.embedding_service = embedding_service

        logger.info("渠道政策分析智能体初始化完成")

    def load_document_tables(self, doc_path: str) -> bool:
        """加载文档中的表格"""
        try:
            if doc_path.endswith('.docx'):
                self.table_analyzer.load_from_docx(doc_path)
            elif doc_path.endswith('.xlsx'):
                self.table_analyzer.load_from_xlsx(doc_path)
            else:
                logger.warning(f"不支持的文件格式: {doc_path}")
                return False

            logger.info(f"成功加载表格: {doc_path}")
            return True

        except Exception as e:
            logger.error(f"加载表格失败: {e}")
            return False

    async def query(self, user_query: str, top_k: int = 10) -> AgentResponse:
        """
        处理用户查询

        Args:
            user_query: 用户查询
            top_k: 返回结果数量

        Returns:
            AgentResponse: 智能体响应
        """
        logger.info(f"处理查询: {user_query}")

        reasoning = []
        sources = []

        # 步骤 1: 理解查询
        reasoning.append("步骤1: 分析查询意图和实体")
        query_analysis = self.query_understander.understand(user_query)
        reasoning.append(f"  - 意图: {query_analysis.intent.value}")
        reasoning.append(f"  - 实体: {len(query_analysis.entities)}个")
        reasoning.append(f"  - 查询类型: {query_analysis.query_type}")

        # 步骤 2: 执行检索
        reasoning.append("\n步骤2: 执行多源检索")

        # 2.1 表格检索
        reasoning.append("  2.1 检索表格数据...")
        table_results = self.table_analyzer.query(
            user_query,
            filters=query_analysis.filters
        )

        reasoning.append(f"       找到 {len(table_results)} 个表格结果")

        # 2.2 向量检索
        vector_results = []
        if self.hybrid_retriever:
            reasoning.append("  2.2 执行混合检索...")
            vector_results = self.hybrid_retriever.hybrid_search(
                query=user_query,
                top_k=top_k
            )
            reasoning.append(f"       找到 {len(vector_results)} 个文档结果")

        # 步骤 3: 综合分析
        reasoning.append("\n步骤3: 综合分析结果")
        answer = self._synthesize_answer(
            query_analysis,
            table_results,
            vector_results,
            reasoning
        )

        # 收集来源
        for tr in table_results:
            sources.append({
                "type": "table",
                "table_index": tr.source_table,
                "confidence": tr.confidence,
                "explanation": tr.explanation
            })

        for vr in vector_results[:3]:
            sources.append({
                "type": "document",
                "id": vr.get("id", ""),
                "score": vr.get("score", 0),
                "source": vr.get("source_document", "")
            })

        # 计算整体置信度
        confidence = self._calculate_confidence(
            query_analysis,
            table_results,
            vector_results
        )

        response = AgentResponse(
            answer=answer,
            sources=sources,
            confidence=confidence,
            reasoning=reasoning,
            metadata={
                "intent": query_analysis.intent.value,
                "query_type": query_analysis.query_type,
                "entities": [{"type": e.entity_type, "value": e.value}
                            for e in query_analysis.entities],
                "table_results_count": len(table_results),
                "vector_results_count": len(vector_results)
            }
        )

        logger.info(f"查询完成: confidence={confidence:.2f}")
        return response

    def _synthesize_answer(self, query_analysis: QueryAnalysis,
                          table_results: List[QueryResult],
                          vector_results: List[Dict],
                          reasoning: List[str]) -> str:
        """综合分析生成答案"""

        intent = query_analysis.intent
        answer_parts = []

        # 根据意图生成不同类型的答案
        if intent == QueryIntent.FEE_CALCULATION:
            answer_parts = self._generate_fee_answer(
                query_analysis, table_results, vector_results, reasoning
            )

        elif intent == QueryIntent.COMMISSION_QUERY:
            answer_parts = self._generate_commission_answer(
                query_analysis, table_results, vector_results, reasoning
            )

        elif intent == QueryIntent.ELIGIBILITY_CHECK:
            answer_parts = self._generate_eligibility_answer(
                query_analysis, table_results, vector_results, reasoning
            )

        elif intent == QueryIntent.COMPARISON:
            answer_parts = self._generate_comparison_answer(
                query_analysis, table_results, vector_results, reasoning
            )

        else:
            answer_parts = self._generate_general_answer(
                query_analysis, table_results, vector_results, reasoning
            )

        # 组合答案
        if not answer_parts:
            return "抱歉，没有找到相关信息。请尝试更具体的查询，例如：'59元套餐的分成是多少？'"

        return "\n\n".join(answer_parts)

    def _generate_fee_answer(self, query_analysis: QueryAnalysis,
                            table_results: List[QueryResult],
                            vector_results: List[Dict],
                            reasoning: List[str]) -> List[str]:
        """生成费用类答案"""
        parts = []

        # 优先使用表格结果
        if table_results:
            reasoning.append("    - 使用表格数据生成答案")
            for tr in table_results[:2]:
                parts.append(f"💰 费用信息:\n{tr.answer}")

        # 补充文档结果
        if vector_results:
            reasoning.append("    - 补充文档说明")
            relevant_docs = [vr for vr in vector_results if vr.get("score", 0) > 0.5]
            if relevant_docs:
                parts.append(f"\n📄 相关说明:\n{relevant_docs[0].get('text', '')[:200]}...")

        return parts

    def _generate_commission_answer(self, query_analysis: QueryAnalysis,
                                   table_results: List[QueryResult],
                                   vector_results: List[Dict],
                                   reasoning: List[str]) -> List[str]:
        """生成佣金类答案"""
        parts = []

        if table_results:
            reasoning.append("    - 使用表格数据")
            for tr in table_results[:2]:
                parts.append(f"📊 分成信息:\n{tr.answer}")

        # 提取详细规则
        if vector_results:
            reasoning.append("    - 提取详细规则")
            for vr in vector_results[:2]:
                if "分成" in vr.get("text", "") or "递延" in vr.get("text", ""):
                    parts.append(f"\n📖 详细规则:\n{vr.get('text', '')[:300]}...")
                    break

        return parts

    def _generate_eligibility_answer(self, query_analysis: QueryAnalysis,
                                    table_results: List[QueryResult],
                                    vector_results: List[Dict],
                                    reasoning: List[str]) -> List[str]:
        """生成资格检查类答案"""
        parts = []

        # 从表格中查找适用性信息
        if table_results:
            reasoning.append("    - 查找适用规则")
            for tr in table_results:
                if "适用" in tr.answer:
                    parts.append(f"✅ 适用规则:\n{tr.answer}")
                    break

        # 补充条件说明
        if vector_results:
            reasoning.append("    - 查找条件说明")
            for vr in vector_results[:2]:
                if "条件" in vr.get("text", "") or "要求" in vr.get("text", ""):
                    parts.append(f"\n📋 条件说明:\n{vr.get('text', '')[:300]}...")
                    break

        return parts

    def _generate_comparison_answer(self, query_analysis: QueryAnalysis,
                                   table_results: List[QueryResult],
                                   vector_results: List[Dict],
                                   reasoning: List[str]) -> List[str]:
        """生成对比类答案"""
        parts = []

        if table_results:
            reasoning.append("    - 从表格提取对比信息")
            parts.append("📊 对比信息:\n")
            for tr in table_results[:2]:
                parts.append(tr.answer)

        if vector_results:
            reasoning.append("    - 补充差异说明")
            for vr in vector_results[:2]:
                if "差异" in vr.get("text", "") or "不同" in vr.get("text", ""):
                    parts.append(f"\n📝 差异说明:\n{vr.get('text', '')[:300]}...")

        return parts

    def _generate_general_answer(self, query_analysis: QueryAnalysis,
                                table_results: List[QueryResult],
                                vector_results: List[Dict],
                                reasoning: List[str]) -> List[str]:
        """生成通用答案"""
        parts = []

        if table_results:
            reasoning.append("    - 使用表格结果")
            parts.append(f"📋 相关信息:\n{table_results[0].answer}")

        if vector_results:
            reasoning.append("    - 使用文档结果")
            parts.append(f"\n📄 详细说明:\n{vector_results[0].get('text', '')[:400]}...")

        return parts

    def _calculate_confidence(self, query_analysis: QueryAnalysis,
                            table_results: List[QueryResult],
                            vector_results: List[Dict]) -> float:
        """计算整体置信度"""
        confidence = 0.0

        # 表格结果置信度
        if table_results:
            table_conf = max(tr.confidence for tr in table_results)
            confidence += table_conf * 0.6

        # 文档结果置信度
        if vector_results:
            vector_conf = max(vr.get("score", 0) for vr in vector_results)
            confidence += vector_conf * 0.4

        return min(confidence, 1.0)


# 单例模式
_agent = None


def get_channel_policy_agent(vector_storage=None, embedding_service=None,
                            hybrid_retriever=None) -> ChannelPolicyAgent:
    """获取智能体实例"""
    global _agent
    if _agent is None:
        _agent = ChannelPolicyAgent(
            vector_storage=vector_storage,
            embedding_service=embedding_service,
            hybrid_retriever=hybrid_retriever
        )
    return _agent

"""
MasterGraph - 激进优化版 (1步流程)
专为deepseek-r1:32B设计，最大化性能
"""

import logging
import time
from typing import Dict, Any, List
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage

from langgraph_agents.state import AgentState, create_initial_state

logger = logging.getLogger(__name__)


class OneStepMasterGraph:
    """
    激进优化版MasterGraph - 1步流程

    优化策略:
    1. 移除独立的意图识别步骤
    2. 移除独立的检索步骤
    3. 在单个LLM调用中完成: 意图分析 + 检索决策 + 答案生成
    4. 利用deepseek-r1:32B的强大推理能力处理所有逻辑

    预期效果: 120秒 → 15-30秒 (提速75-87%)
    """

    # 超简洁提示词 - 1步完成所有任务
    ONE_STEP_PROMPT = """你是渠道业务查询专家。基于提供的文档信息回答用户问题。

【回答格式】
【直接回答】简明答案
【详细说明】数据和分析
【数据来源】文档名称

要求：数据准确、简洁、来自提供的文档"""

    def __init__(
        self,
        llm: ChatOllama,
        hybrid_retriever=None,
        table_analyzer=None
    ):
        self.llm = llm
        self.hybrid_retriever = hybrid_retriever
        self.table_analyzer = table_analyzer

        # 构建极简版1步流程图
        self.graph = self._build_one_step_graph()
        logger.info("✅ 激进优化版MasterGraph初始化完成 (1步流程)")

    def _build_one_step_graph(self) -> StateGraph:
        """构建1步流程图: 直接生成"""
        workflow = StateGraph(AgentState)
        workflow.add_node("one_step_generate", self._one_step_generate)
        workflow.set_entry_point("one_step_generate")
        workflow.add_edge("one_step_generate", END)
        return workflow.compile()

    async def _one_step_generate(self, state: AgentState) -> AgentState:
        """
        1步完成所有任务: 检索 + 生成

        优化: 在提示词中让LLM自己判断需要什么信息，
        然后我们一次性提供所有相关文档，生成答案
        """
        query = state["user_query"]
        chat_history = state.get("chat_history", [])

        logger.info(f"🚀 1步生成开始: query={query}")

        start_time = time.time()

        try:
            # 步骤1: 快速检索相关文档 (传统代码，不调用LLM)
            retrieved_docs = await self._fast_retrieve(query)

            # 步骤2: 构建简洁的上下文
            context = self._build_ultra_simple_context(retrieved_docs)

            # 步骤3: 单次LLM调用完成所有任务
            user_prompt = f"""问题：{query}

文档信息：
{context}

请基于以上文档回答问题。"""

            messages = [
                SystemMessage(content=self.ONE_STEP_PROMPT),
                HumanMessage(content=user_prompt)
            ]

            # 单次生成
            response = await self.llm.ainvoke(messages)
            answer = response.content

            generation_time = time.time() - start_time
            logger.info(f"✅ 1步生成完成: {len(answer)}字符, 耗时{generation_time:.2f}秒")

            # 更新状态
            state["answer"] = answer
            state["generation_time"] = generation_time
            state["retrieved_docs"] = retrieved_docs
            state["intent"] = "general"  # 跳过意图识别
            state["rewritten_query"] = query

            return state

        except Exception as e:
            logger.error(f"❌ 1步生成失败: {e}")
            generation_time = time.time() - start_time
            state["answer"] = f"抱歉，处理查询时出现错误: {str(e)}"
            state["generation_time"] = generation_time
            return state

    async def _fast_retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        快速检索 - 不使用LLM，直接向量搜索

        优化: 移除意图分析、查询重写等LLM调用
        """
        if not self.hybrid_retriever:
            return []

        try:
            # 使用hybrid_search方法
            results = self.hybrid_retriever.hybrid_search(
                query=query,
                top_k=top_k,
                fusion_method="rrf",
                use_rerank=False
            )

            logger.info(f"📚 快速检索: {len(results)}个文档")
            return results

        except Exception as e:
            logger.error(f"❌ 检索失败: {e}")
            return []

    def _build_ultra_simple_context(self, docs: List[Dict]) -> str:
        """
        构建超简洁的文档上下文

        优化: 限制文档数量和长度，减少token
        """
        if not docs:
            return "无相关文档信息"

        # 只取前3个最相关的文档
        top_docs = docs[:3]
        context_parts = []

        for i, doc in enumerate(top_docs):
            text = doc.get("text", doc.get("chunk_text", ""))
            source = doc.get("source_document", doc.get("filename", "未知"))
            score = doc.get("score", 0)

            # 严格限制长度，避免token过多
            max_length = 800
            if len(text) > max_length:
                text = text[:max_length] + "..."

            context_parts.append(f"[文档{i+1}] {source} (相关度:{score:.2f})\n{text}")

        return "\n\n".join(context_parts)

    def process(
        self,
        user_query: str,
        session_id: str = None,
        chat_history: list = None,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        同步处理查询 (1步流程)

        兼容原MasterGraph接口

        Args:
            user_query: 用户查询
            session_id: 会话ID (可选)
            chat_history: 对话历史 (可选)
            config: 额外配置 (可选)

        Returns:
            处理结果字典

        预期时间: 15-30秒 (vs 原来120秒)
        """
        logger.info(f"🎯 1步流程处理 (同步): {user_query}")

        initial_state = create_initial_state(user_query, chat_history or [])
        final_state = self.graph.invoke(initial_state)

        return {
            "success": True,
            "answer": final_state.get("answer", ""),
            "generation_time": final_state.get("generation_time", 0),
            "retrieved_docs": final_state.get("retrieved_docs", []),
            "optimization_mode": "one_step",
            "session_id": session_id
        }

    async def aprocess(
        self,
        user_query: str,
        session_id: str = None,
        chat_history: list = None,
        config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        异步处理查询 (1步流程)

        兼容原MasterGraph接口

        Args:
            user_query: 用户查询
            session_id: 会话ID (可选)
            chat_history: 对话历史 (可选)
            config: 额外配置 (可选)

        Returns:
            处理结果字典

        预期时间: 15-30秒 (vs 原来120秒)
        """
        logger.info(f"🎯 1步流程处理 (异步): {user_query}")

        initial_state = create_initial_state(user_query, chat_history or [])
        final_state = await self.graph.ainvoke(initial_state)

        return {
            "success": True,
            "answer": final_state.get("answer", ""),
            "generation_time": final_state.get("generation_time", 0),
            "retrieved_docs": final_state.get("retrieved_docs", []),
            "optimization_mode": "one_step",
            "session_id": session_id
        }


# ==================== 智能计算检测器 ====================

class SmartCalculationDetector:
    """
    智能计算检测器 - 将计算任务分离到传统代码

    优化: 检测计算类问题，使用Python代码而非LLM
    """

    # 计算关键词
    CALCULATION_KEYWORDS = [
        '计算', '求和', '总计', '合计', '汇总',
        '费用', '金额', '价格', '成本',
        '多少', '几个', '总数', '平均'
    ]

    # 表格查询关键词
    TABLE_KEYWORDS = [
        '表格', '列表', '清单',
        '渠道', '产品', '业务',
        '费率', '政策', '标准'
    ]

    @classmethod
    def is_calculation_query(cls, query: str) -> bool:
        """检测是否为计算类问题"""
        query_lower = query.lower()
        return any(kw in query_lower for kw in cls.CALCULATION_KEYWORDS)

    @classmethod
    def is_table_query(cls, query: str) -> bool:
        """检测是否为表格查询"""
        query_lower = query.lower()
        return any(kw in query_lower for kw in cls.TABLE_KEYWORDS)

    @classmethod
    def detect_query_type(cls, query: str) -> str:
        """
        智能检测查询类型

        Returns:
            'calculation': 计算类问题
            'table': 表格查询
            'general': 一般推理
        """
        if cls.is_calculation_query(query):
            return 'calculation'
        elif cls.is_table_query(query):
            return 'table'
        else:
            return 'general'


# ==================== 极简配置加载器 ====================

def create_optimized_master_graph(
    llm: ChatOllama,
    hybrid_retriever=None,
    table_analyzer=None,
    mode: str = "one_step"  # "one_step" 或 "two_step"
):
    """
    创建优化版MasterGraph的工厂函数

    Args:
        llm: LLM实例
        hybrid_retriever: 混合检索器
        table_analyzer: 表格分析器
        mode: 优化模式
            - "one_step": 激进优化 (1步流程)
            - "two_step": 保守优化 (2步流程)
    """
    if mode == "one_step":
        logger.info("🚀 使用激进优化模式 (1步流程)")
        return OneStepMasterGraph(llm, hybrid_retriever, table_analyzer)
    else:
        logger.info("⚡ 使用保守优化模式 (2步流程)")
        # 这里可以返回2步流程版本
        return UltraSimpleMasterGraph(llm, hybrid_retriever, table_analyzer)

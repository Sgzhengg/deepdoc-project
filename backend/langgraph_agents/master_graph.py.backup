"""
MasterGraph - LangGraph工作流图
DeepDoc多Agent系统的核心工作流编排
"""

import logging
from typing import Any, Dict
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END

from .state import AgentState, create_initial_state
from .nodes.intent_agent import create_intent_agent
from .nodes.retrieval_agent import create_retrieval_agent
from .nodes.reasoning_agent import create_reasoning_agent
from .nodes.generate_agent import create_generate_agent
from .nodes.synthesis_agent import create_synthesis_agent
from .edges.conditional_edges import decide_retrieval_strategy

logger = logging.getLogger(__name__)


class MasterGraph:
    """
    MasterGraph - 多Agent工作流编排器

    使用LangGraph构建基于状态机的多Agent协作系统
    """

    def __init__(
        self,
        llm: ChatOllama,
        hybrid_retriever=None,
        table_analyzer=None,
        use_checkpointer: bool = False
    ):
        """
        初始化MasterGraph

        Args:
            llm: LLM实例
            hybrid_retriever: 混合检索器
            table_analyzer: 表格分析器
            use_checkpointer: 是否使用检查点（支持中断和恢复）
        """
        self.llm = llm
        self.hybrid_retriever = hybrid_retriever
        self.table_analyzer = table_analyzer

        # 创建Agent实例（优化：仅保留核心Agent）
        self.intent_agent = create_intent_agent(llm=llm)
        self.retrieval_agent = create_retrieval_agent(
            hybrid_retriever=hybrid_retriever,
            table_analyzer=table_analyzer,
            llm=llm
        )
        # self.reasoning_agent = create_reasoning_agent(llm=llm)  # 移除：功能合并到generate
        self.generate_agent = create_generate_agent(llm=llm)
        # self.synthesis_agent = create_synthesis_agent()  # 移除：功能合并到generate

        # 构建工作流图
        self.graph = self._build_graph(use_checkpointer)

        logger.info("✅ MasterGraph初始化完成")

    def _build_graph(self, use_checkpointer: bool) -> StateGraph:
        """
        构建LangGraph工作流图（优化版：减少节点数量）

        Args:
            use_checkpointer: 是否使用检查点

        Returns:
            编译后的StateGraph
        """
        logger.info("🔨 构建LangGraph工作流（优化版：3节点流程）...")

        # 创建状态图
        workflow = StateGraph(AgentState)

        # ========== 添加节点（仅保留核心节点）==========
        workflow.add_node("intent", self.intent_agent)
        workflow.add_node("retrieve", self.retrieval_agent)
        workflow.add_node("generate", self.generate_agent)

        # ========== 设置入口 ==========
        workflow.set_entry_point("intent")

        # ========== 添加边（优化：3步流程）==========
        # 意图识别 -> 执行检索 -> 生成答案 -> 结束
        workflow.add_edge("intent", "retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)

        # ========== 编译工作流 ==========
        compiled_graph = workflow.compile()
        logger.info("✅ 工作流编译完成（优化版：3节点流程）")

        return compiled_graph

    async def aprocess(
        self,
        user_query: str,
        session_id: str = None,
        chat_history: list = None,
        config: dict = None
    ) -> Dict[str, Any]:
        """
        异步处理用户查询

        Args:
            user_query: 用户查询
            session_id: 会话ID
            chat_history: 对话历史
            config: 额外配置（如max_iterations）

        Returns:
            处理结果字典
        """
        logger.info(f"🚀 开始处理查询: {user_query}")

        try:
            # 创建初始状态
            initial_state = create_initial_state(
                user_query=user_query,
                session_id=session_id,
                chat_history=chat_history,
                max_iterations=config.get("max_iterations", 3) if config else 3
            )

            # 运行工作流
            config_dict = {
                "configurable": {"thread_id": session_id},
                "recursion_limit": 10  # 线性流程，降低递归限制
            } if session_id else {"recursion_limit": 10}

            result = await self.graph.ainvoke(
                initial_state,
                config=config_dict
            )

            # 提取结果
            reasoning_steps = result.get("reasoning_steps", [])
            logger.info(f"📊 最终推理步骤数量: {len(reasoning_steps)}")
            for i, step in enumerate(reasoning_steps):
                logger.info(f"  步骤{i}: {step[:50]}...")

            response = {
                "success": True,
                "answer": result.get("final_answer", ""),
                "reasoning": reasoning_steps,
                "sources": result.get("sources", []),
                "confidence": result.get("confidence", 0.0),
                "metadata": result.get("metadata", {}),
                "session_id": session_id
            }

            logger.info(f"✅ 查询处理完成, confidence={response['confidence']:.2f}")

            return response

        except Exception as e:
            logger.error(f"❌ 处理查询失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": "抱歉，处理您的查询时出现错误。"
            }

    def process(
        self,
        user_query: str,
        session_id: str = None,
        chat_history: list = None,
        config: dict = None
    ) -> Dict[str, Any]:
        """
        同步处理用户查询

        Args:
            user_query: 用户查询
            session_id: 会话ID
            chat_history: 对话历史
            config: 额外配置

        Returns:
            处理结果字典
        """
        logger.info(f"🚀 开始处理查询: {user_query}")

        try:
            # 创建初始状态
            initial_state = create_initial_state(
                user_query=user_query,
                session_id=session_id,
                chat_history=chat_history,
                max_iterations=config.get("max_iterations", 3) if config else 3
            )

            # 运行工作流
            config_dict = {
                "configurable": {"thread_id": session_id},
                "recursion_limit": 10  # 线性流程，降低递归限制
            } if session_id else {"recursion_limit": 10}

            result = self.graph.invoke(
                initial_state,
                config=config_dict
            )

            # 提取结果
            reasoning_steps = result.get("reasoning_steps", [])
            logger.info(f"📊 最终推理步骤数量: {len(reasoning_steps)}")
            for i, step in enumerate(reasoning_steps):
                logger.info(f"  步骤{i}: {step[:50]}...")

            response = {
                "success": True,
                "answer": result.get("final_answer", ""),
                "reasoning": reasoning_steps,
                "sources": result.get("sources", []),
                "confidence": result.get("confidence", 0.0),
                "metadata": result.get("metadata", {}),
                "session_id": session_id
            }

            logger.info(f"✅ 查询处理完成, confidence={response['confidence']:.2f}")

            return response

        except Exception as e:
            logger.error(f"❌ 处理查询失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": "抱歉，处理您的查询时出现错误。"
            }


def create_master_graph(
    llm: ChatOllama,
    hybrid_retriever=None,
    table_analyzer=None,
    use_checkpointer: bool = False
) -> MasterGraph:
    """
    创建MasterGraph实例的工厂函数

    Args:
        llm: LLM实例
        hybrid_retriever: 混合检索器
        table_analyzer: 表格分析器
        use_checkpointer: 是否使用检查点

    Returns:
        MasterGraph实例
    """
    return MasterGraph(
        llm=llm,
        hybrid_retriever=hybrid_retriever,
        table_analyzer=table_analyzer,
        use_checkpointer=use_checkpointer
    )

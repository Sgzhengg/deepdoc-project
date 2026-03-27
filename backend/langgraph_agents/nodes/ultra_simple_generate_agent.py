"""
GenerateAgent - 极简优化版
专门为deepseek-r1:32B优化，大幅简化提示词和逻辑
"""

import logging
from typing import Dict, Any
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph_agents.state import AgentState

logger = logging.getLogger(__name__)


class UltraSimpleGenerateAgent:
    """
    极简版生成Agent - 专为deepseek-r1:32B优化

    优化策略:
    1. 超简洁提示词 (100-200 tokens)
    2. 移除所有验证和重试
    3. 单次生成，信任模型输出
    4. 利用deepseek-r1:32B的强大推理能力
    """

    # 极简提示词 - 利用deepseek-r1:32B的能力
    ULTRA_SIMPLE_PROMPT = """基于文档回答问题。

【直接回答】
【数据来源】

要求：数据准确、简洁、来自文档"""

    def __init__(self, llm: ChatOllama):
        self.llm = llm
        logger.info("✅ 使用极简版GenerateAgent (专为deepseek-r1:32B优化)")

    async def __call__(self, state: AgentState) -> AgentState:
        """
        生成答案 (极简版 - 单次调用，无验证)
        """
        query = state.get("rewritten_query", state["user_query"])
        docs = state.get("retrieved_docs", [])

        logger.info(f"极简生成: query={query}, docs={len(docs)}")

        # 构建超简洁的提示
        context = self._build_simple_context(docs)
        user_prompt = f"文档：{context}\n\n问题：{query}"

        try:
            # 单次生成调用，无验证，无重试
            messages = [
                SystemMessage(content=self.ULTRA_SIMPLE_PROMPT),
                HumanMessage(content=user_prompt)
            ]

            # 直接调用LLM
            start_time = time.time()
            response = await self.llm.ainvoke(messages)
            generation_time = time.time() - start_time

            answer = response.content
            logger.info(f"✅ 极简生成完成: {len(answer)}字符, 耗时{generation_time:.2f}秒")

            # 更新状态
            state["answer"] = answer
            state["generation_time"] = generation_time
            state["retry_count"] = 0  # 无重试

            return state

        except Exception as e:
            logger.error(f"❌ 极简生成失败: {e}")
            state["answer"] = f"抱歉，生成答案时出现错误: {str(e)}"
            state["generation_time"] = 0
            return state

    def _build_simple_context(self, docs: list) -> str:
        """构建简洁的文档上下文"""
        if not docs:
            return "无相关文档"

        # 只取前3个最相关的文档，限制长度
        relevant_docs = docs[:3]
        context_parts = []

        for i, doc in enumerate(relevant_docs):
            # 提取关键信息，限制长度
            text = doc.get("text", doc.get("chunk_text", ""))
            source = doc.get("source_document", doc.get("filename", "未知来源"))

            # 限制每个文档的长度，避免token过多
            if len(text) > 500:
                text = text[:500] + "..."

            context_parts.append(f"[文档{i+1}] {source}\n{text}")

        return "\n\n".join(context_parts)


def create_ultra_simple_generate_agent(llm: ChatOllama):
    """创建极简版生成Agent工厂函数"""
    return UltraSimpleGenerateAgent(llm)


# ==================== 极简版MasterGraph ====================

class UltraSimpleMasterGraph:
    """
    极简版MasterGraph - 2步流程优化

    优化: 意图识别 → 检索+生成 (合并步骤)
    """

    def __init__(self, llm, hybrid_retriever=None, table_analyzer=None):
        self.llm = llm
        self.hybrid_retriever = hybrid_retriever
        self.table_analyzer = table_analyzer

        # 创建简化的agents
        from .nodes.intent_agent import create_intent_agent
        from .nodes.retrieval_agent import create_retrieval_agent

        self.intent_agent = create_intent_agent(llm=llm)
        self.retrieve_agent = create_retrieval_agent(
            hybrid_retriever=hybrid_retriever,
            table_analyzer=table_analyzer,
            llm=llm
        )
        self.generate_agent = create_ultra_simple_generate_agent(llm=llm)

        # 构建简化版图
        self.graph = self._build_simple_graph()
        logger.info("✅ 极简版MasterGraph初始化完成 (2步流程)")

    def _build_simple_graph(self):
        """构建2步流程图: 意图 → 检索+生成"""
        from langgraph.graph import StateGraph, END

        workflow = StateGraph(AgentState)
        workflow.add_node("intent", self.intent_agent)
        workflow.add_node("retrieve_and_generate", self._retrieve_and_generate)

        workflow.set_entry_point("intent")
        workflow.add_edge("intent", "retrieve_and_generate")
        workflow.add_edge("retrieve_and_generate", END)

        return workflow.compile()

    async def _retrieve_and_generate(self, state: AgentState) -> AgentState:
        """合并的检索+生成步骤"""
        # 执行检索
        state = await self.retrieve_agent(state)

        # 直接执行生成（无中间验证）
        state = await self.generate_agent(state)

        return state

    async def aprocess(self, query: str, chat_history: list = None) -> Dict[str, Any]:
        """处理查询（极简版）"""
        initial_state = create_initial_state(query, chat_history or [])
        final_state = await self.graph.ainvoke(initial_state)

        return {
            "answer": final_state.get("answer", ""),
            "generation_time": final_state.get("generation_time", 0),
            "retrieved_docs": final_state.get("retrieved_docs", [])
        }


import time  # 移到顶部
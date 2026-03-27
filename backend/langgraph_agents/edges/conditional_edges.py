"""
条件边函数 - LangGraph工作流的路由决策
"""

import logging
from typing import Literal
from ..state import AgentState

logger = logging.getLogger(__name__)


def decide_retrieval_strategy(state: AgentState) -> str:
    """
    决定检索策略

    Args:
        state: 当前状态

    Returns:
        检索策略: "table", "hybrid", "vector"
    """
    intent = state.get("intent", "")
    query_type = state.get("query_type", "")

    logger.info(f"决策检索策略: intent={intent}, query_type={query_type}")

    # 表格查询优先使用表格检索
    if intent == "table_query":
        return "table"

    # 复杂查询使用混合检索
    if query_type in ["complex", "multi_step"]:
        return "hybrid"

    # 默认使用向量检索
    return "vector"


def should_reretrieve(state: AgentState) -> Literal["reretrieve", "continue"]:
    """
    Self-RAG: 判断是否需要重新检索

    Args:
        state: 当前状态

    Returns:
        "reretrieve" 或 "continue"
    """
    quality = state.get("retrieval_quality", 0.0)
    current_iteration = state.get("current_iteration", 0)
    max_iterations = 1  # 固定为1次，避免不必要的循环

    logger.info(f"评估是否重新检索: quality={quality:.2f}, iteration={current_iteration}/{max_iterations}")

    # 如果有文档就直接继续，不重新检索
    docs = state.get("retrieved_docs", [])
    if docs and len(docs) > 0:
        logger.info("→ 已检索到文档，继续推理")
        return "continue"

    # 第一次迭代时尝试重新检索
    if current_iteration < max_iterations:
        logger.info("→ 决策: 首次未检索到文档，重新检索")
        return "reretrieve"

    logger.info("→ 决策: 继续推理")
    return "continue"


def should_regenerate(state: AgentState) -> Literal["regenerate", "finalize"]:
    """
    Self-RAG: 判断是否需要重新生成答案

    Args:
        state: 当前状态

    Returns:
        "regenerate" 或 "finalize"
    """
    quality = state.get("answer_quality", 0.0) or state.get("confidence", 0.0)
    current_iteration = state.get("current_iteration", 0)

    logger.info(f"评估是否重新生成: quality={quality:.2f}, iteration={current_iteration}")

    # 总是直接完成，避免循环（移除重新生成逻辑）
    logger.info("→ 决策: 完成处理")
    return "finalize"


def decide_next_step(state: AgentState) -> str:
    """
    决定下一步操作（综合决策）

    Args:
        state: 当前状态

    Returns:
        下一步: "retrieve", "reason", "end"
    """
    intent = state.get("intent", "")
    docs = state.get("retrieved_docs", [])

    # 如果没有文档，需要检索
    if not docs:
        return "retrieve"

    # 如果有文档，进行推理
    return "reason"

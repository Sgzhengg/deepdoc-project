"""
AgentState - LangGraph工作流状态定义
定义在Agent节点间传递的状态数据结构
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator


class AgentState(TypedDict):
    """
    Agent状态类 - LangGraph工作流的核心数据结构

    这个状态在所有Agent节点之间传递，每个节点可以读取和更新状态
    """

    # ========== 输入 ==========
    user_query: str                          # 用户原始查询
    session_id: Optional[str]                # 会话ID
    chat_history: Annotated[List[Dict[str, str]], operator.add]  # 对话历史（累加）

    # ========== 意图理解 ==========
    intent: str                              # 意图类型
                                            # 可选值: "search", "analyze", "compare",
                                            #         "calculate", "table_query", "general"
    query_type: str                          # 查询类型
                                            # 可选值: "simple", "complex", "multi_step"
    entities: List[Dict[str, Any]]           # 提取的实体（如套餐名称、费用类型等）
    rewritten_query: str                     # 重写和优化后的查询

    # ========== 检索相关 ==========
    retrieval_strategy: str                  # 检索策略
                                            # 可选值: "vector", "hybrid", "table", "adaptive"
    retrieved_docs: List[Dict[str, Any]]     # 检索到的文档列表
    retrieval_scores: List[float]            # 检索分数列表
    retrieval_quality: float                 # 检索质量评分（0-1）

    # ========== 推理和分析 ==========
    reasoning_steps: Annotated[List[str], operator.add]  # 推理步骤（累加）
    analysis_results: Dict[str, Any]         # 分析结果（包含计算、提取的数据等）
    table_results: List[Dict[str, Any]]      # 表格查询结果

    # ========== 生成相关 ==========
    draft_answer: str                        # 草稿答案
    final_answer: str                        # 最终答案
    answer_quality: float                    # 答案质量评分（0-1）

    # ========== 元数据 ==========
    sources: List[Dict[str, Any]]            # 数据来源列表
    confidence: float                        # 整体置信度（0-1）
    metadata: Dict[str, Any]                 # 额外的元数据信息

    # ========== 控制标志 ==========
    should_reretrieve: bool                  # 是否需要重新检索
    should_regenerate: bool                  # 是否需要重新生成
    max_iterations: int                      # 最大迭代次数
    current_iteration: int                   # 当前迭代次数


def create_initial_state(
    user_query: str,
    session_id: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    max_iterations: int = 3
) -> AgentState:
    """
    创建初始状态

    Args:
        user_query: 用户查询
        session_id: 会话ID
        chat_history: 对话历史
        max_iterations: 最大迭代次数

    Returns:
        初始化的AgentState
    """
    return {
        "user_query": user_query,
        "session_id": session_id,
        "chat_history": chat_history or [],

        # 意图理解 - 初始化为空
        "intent": "",
        "query_type": "",
        "entities": [],
        "rewritten_query": "",

        # 检索相关 - 初始化为空
        "retrieval_strategy": "",
        "retrieved_docs": [],
        "retrieval_scores": [],
        "retrieval_quality": 0.0,

        # 推理和分析 - 初始化为空
        "reasoning_steps": [],
        "analysis_results": {},
        "table_results": [],

        # 生成相关 - 初始化为空
        "draft_answer": "",
        "final_answer": "",
        "answer_quality": 0.0,

        # 元数据 - 初始化为空
        "sources": [],
        "confidence": 0.0,
        "metadata": {},

        # 控制标志
        "should_reretrieve": False,
        "should_regenerate": False,
        "max_iterations": max_iterations,
        "current_iteration": 0
    }


def state_to_dict(state: AgentState) -> Dict[str, Any]:
    """
    将AgentState转换为普通字典（用于JSON序列化）

    Args:
        state: AgentState对象

    Returns:
        可序列化的字典
    """
    return {
        "user_query": state.get("user_query", ""),
        "session_id": state.get("session_id"),
        "intent": state.get("intent", ""),
        "query_type": state.get("query_type", ""),
        "entities": state.get("entities", []),
        "rewritten_query": state.get("rewritten_query", ""),
        "retrieval_strategy": state.get("retrieval_strategy", ""),
        "retrieval_docs_count": len(state.get("retrieved_docs", [])),
        "retrieval_quality": state.get("retrieval_quality", 0.0),
        "reasoning_steps": state.get("reasoning_steps", []),
        "table_results_count": len(state.get("table_results", [])),
        "final_answer": state.get("final_answer", ""),
        "confidence": state.get("confidence", 0.0),
        "sources": state.get("sources", []),
        "current_iteration": state.get("current_iteration", 0),
        "metadata": state.get("metadata", {})
    }

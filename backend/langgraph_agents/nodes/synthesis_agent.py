"""
SynthesisAgent - 综合智能体
负责整合所有信息，生成最终响应
"""

import logging
from typing import Dict, Any
from ..state import AgentState
from ..tools.reasoning_translator import get_reasoning_translator

logger = logging.getLogger(__name__)


class SynthesisAgent:
    """
    综合Agent

    功能：
    1. 整合答案：整合各Agent的输出
    2. 生成响应：构建最终响应结构
    3. 元数据整理：整理元数据和来源
    """

    def __init__(self):
        """初始化SynthesisAgent"""
        pass

    def __call__(self, state: AgentState) -> AgentState:
        """
        综合处理

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("SynthesisAgent: 综合处理最终响应")

        try:
            # 最终答案已经由GenerateAgent生成
            # 这里主要是确保所有字段都正确设置

            # ========== 修复问题3：翻译推理步骤为用户友好的语言 ==========
            reasoning_steps = state.get("reasoning_steps", [])

            # 使用翻译器将技术化的推理步骤转换为用户友好的语言
            translator = get_reasoning_translator()
            translated_steps = translator.simplify_for_user(reasoning_steps)

            logger.info(f"🔄 推理步骤翻译: {len(reasoning_steps)} -> {len(translated_steps)}")

            state["reasoning_steps"] = translated_steps

            # 整理元数据
            metadata = state.get("metadata", {})
            metadata.update({
                "intent": state.get("intent", ""),
                "query_type": state.get("query_type", ""),
                "retrieval_strategy": state.get("retrieval_strategy", ""),
                "docs_retrieved": len(state.get("retrieved_docs", [])),
                "tables_used": len(state.get("table_results", [])),
                "iterations": state.get("current_iteration", 0)
            })
            state["metadata"] = metadata

            # 确保置信度在合理范围
            confidence = state.get("confidence", 0.0)
            state["confidence"] = max(0.0, min(confidence, 1.0))

        except Exception as e:
            logger.error(f"SynthesisAgent错误: {e}")

        return state


def create_synthesis_agent() -> SynthesisAgent:
    """创建SynthesisAgent实例"""
    return SynthesisAgent()

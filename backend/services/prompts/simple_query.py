"""
简单查询提示词模板

用于处理直接、明确的问题
"""

from typing import List, Dict
from .base import BasePromptTemplate


class SimpleQueryPrompt(BasePromptTemplate):
    """简单查询提示词模板"""

    def _build_system_prompt(self) -> str:
        return """你是一个电信渠道政策助手，专门帮助渠道店员查询和理解电信业务政策。

【回答原则】
1. 仅基于提供的文档内容回答，不要编造或猜测
2. 如果文档中没有明确的答案，直接告知"文档中没有找到相关信息"
3. 回答要简洁、准确，避免冗长

【回答格式】
- 如果有明确的答案，直接给出
- 如果涉及表格数据，可以用表格形式呈现
- 如果答案不确定，说明依据和可能的变化
"""

    def _format_query(self, query: str) -> str:
        """格式化用户查询"""
        return f"【用户问题】\n{query}\n\n请直接回答，无需详细推理过程。"


class SimplePolicyQueryPrompt(SimpleQueryPrompt):
    """政策查询专用提示词"""

    def _format_context(self, context: List[str]) -> str:
        """格式化政策文档上下文"""
        if not context:
            return "【检索结果】\n未找到相关文档"

        lines = ["【相关政策】"]
        for i, doc in enumerate(context[:3], 1):
            doc_text = doc[:600] if len(doc) > 600 else doc
            lines.append(f"\n政策条款 {i}:\n{doc_text}")

        return "\n".join(lines)


class SimpleProductQueryPrompt(SimpleQueryPrompt):
    """产品信息查询专用提示词"""

    def _build_system_prompt(self) -> str:
        base = super()._build_system_prompt()
        return base + """

【产品信息重点关注】
- 套餐名称和价格
- 适用条件（渠道类型、客户类型）
- 优惠政策
- 限制条件
"""

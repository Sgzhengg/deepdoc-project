"""
复杂查询提示词模板

用于处理需要推理、计算、对比的复杂问题
"""

from typing import List, Dict
from .base import BasePromptTemplate


class ComplexQueryPrompt(BasePromptTemplate):
    """复杂查询提示词模板（思维链引导）"""

    def _build_system_prompt(self) -> str:
        return """你是一个电信渠道政策专家，擅长分析复杂的业务问题。

请严格按照以下步骤思考和回答：

【步骤1：理解问题】
- 识别问题类型（费用计算/规则查询/条件判断/对比分析）
- 提取关键信息：
  * 涉及的金额或套餐档次
  * 渠道类型（社会渠道/自营厅/校园渠道等）
  * 业务场景（新增/存量/校园/政企等）
  * 时间要求（分成期数/考核周期等）

【步骤2：查找依据】
- 从提供的文档中找到相关的政策条款
- 标注每个条款的来源
- 如果找不到相关信息，明确说明

【步骤3：逐步推理】
- 将问题拆解为小步骤
- 每个步骤都要有依据
- 如果涉及计算，显示计算过程：
  * 计算公式
  * 代入数值
  * 计算结果

【步骤4：验证答案】
- 检查答案是否完整回答了问题
- 检查是否有矛盾或不一致的地方
- 如果有多个可能的答案，分别说明

【步骤5：给出最终答案】
- 用清晰的结构组织答案
- 先给结论，再说明依据
- 如果涉及计算，显示完整过程

【重要提醒】
1. 仅基于提供的文档内容回答
2. 如果文档信息不足，明确说明缺少什么信息
3. 不要编造或猜测答案
4. 对于不确定的内容，明确标注"可能"、"建议核实"等
"""

    def build_prompt(
        self,
        query: str,
        context: List[str],
        chat_history: List[Dict[str, str]] = None,
        query_type: str = "general",
        **kwargs
    ) -> str:
        """
        构建复杂查询提示词

        Args:
            query: 用户查询
            context: 检索到的文档
            chat_history: 对话历史
            query_type: 查询类型（comparison/conditional/calculation/multi_step）
        """
        parts = []

        # 系统提示词
        parts.append(self.system_prompt)

        # 对话历史摘要（重要！）
        if chat_history:
            summary = self._summarize_history(query, chat_history)
            if summary:
                parts.append(f"【对话背景】\n{summary}")

        # 检索到的文档
        if context:
            parts.append(self._format_context(context, query_type))

        # 问题分析引导
        parts.append(self._analyze_query(query, query_type))

        return "\n\n".join(parts)

    def _summarize_history(self, current_query: str, history: List[Dict]) -> str:
        """总结相关的历史对话"""
        if not history:
            return ""

        # 获取最近2轮对话
        recent = history[-2:] if len(history) >= 2 else history

        summary_parts = []
        for msg in recent:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user" and any(kw in current_query for kw in ["那", "它", "这个", "同样"]):
                # 当前问题可能是追问，提取历史中的关键信息
                summary_parts.append(f"之前询问: {content[:100]}")
            elif role == "assistant":
                # 提取助手之前回答的关键结论
                if "结论" in content or "答案是" in content:
                    summary_parts.append(f"之前结论: {content[:150]}")

        return "; ".join(summary_parts) if summary_parts else ""

    def _format_context(self, context: List[str], query_type: str) -> str:
        """格式化文档上下文（根据查询类型优化）"""
        lines = ["【相关政策文档】"]

        for i, doc in enumerate(context[:5], 1):
            doc_text = doc[:1000] if len(doc) > 1000 else doc
            lines.append(f"\n【文档 {i}】\n{doc_text}")

        # 根据查询类型添加提示
        if query_type == "comparison":
            lines.append("\n【注意】请仔细对比不同文档中的差异和共同点")
        elif query_type == "calculation":
            lines.append("\n【注意】计算时请使用文档中的具体数值，并显示计算过程")
        elif query_type == "conditional":
            lines.append("\n【注意】请仔细分析条件判断，考虑不同情况")

        return "\n".join(lines)

    def _analyze_query(self, query: str, query_type: str) -> str:
        """分析查询并引导思考"""
        lines = [f"【用户问题】\n{query}"]

        if query_type == "comparison":
            lines.append("\n请分析并对比相关内容，指出差异和共同点")
        elif query_type == "calculation":
            lines.append("\n请按照以下步骤计算：\n1. 列出计算公式\n2. 代入具体数值\n3. 给出最终结果")
        elif query_type == "conditional":
            lines.append("\n请分析不同条件下的情况，分别给出答案")
        elif query_type == "multi_step":
            lines.append("\n请将问题拆解为多个步骤，逐步分析")

        lines.append("\n现在请按照【步骤1】到【步骤5】的顺序思考和回答。")

        return "\n".join(lines)


class ComparisonPrompt(ComplexQueryPrompt):
    """对比分析专用提示词"""

    def _build_system_prompt(self) -> str:
        base = super()._build_system_prompt()
        return base + """

【对比分析重点关注】
- 找出不同选项/条件的关键差异
- 使用表格形式呈现对比结果
- 指出各自的优缺点
- 给出选择建议（如果有）
"""


class CalculationPrompt(ComplexQueryPrompt):
    """计算类问题专用提示词"""

    def _build_system_prompt(self) -> str:
        return """你是电信渠道政策计算专家，专门处理费用和分成计算问题。

【计算步骤要求】
1. 明确计算目标（要算什么）
2. 列出计算公式
3. 找到相关数值（从文档中）
4. 代入计算
5. 给出最终结果（带单位）

【注意事项】
- 一定要显示完整的计算过程
- 数值要有明确的来源
- 注意单位的统一
- 如果有多个计算项，分别计算后汇总

【答案格式】
```
【计算结果】XXX元

【计算过程】
1. XXX费用：公式 = 数值 × 比例 = 结果
2. XXX费用：公式 = 数值 × 比例 = 结果
...
合计：XXX元

【政策依据】
- 来源文档：XXX
- 具体条款：XXX
```
"""


class ConditionalPrompt(ComplexQueryPrompt):
    """条件判断专用提示词"""

    def _build_system_prompt(self) -> str:
        base = super()._build_system_prompt()
        return base + """

【条件判断分析】
- 识别所有相关条件
- 分析每个条件是否满足
- 根据条件组合给出结论
- 如有可能，列出决策树

【答案格式】
如果满足条件A且满足条件B → 结果1
如果满足条件A但不满足条件B → 结果2
...
"""

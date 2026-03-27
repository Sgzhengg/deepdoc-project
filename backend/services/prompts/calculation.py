"""
计算类问题提示词模板

用于处理费用、分成、比例等计算问题
"""

from typing import List, Dict, Any
from .base import BasePromptTemplate


class CalculationPromptTemplate(BasePromptTemplate):
    """计算类问题提示词模板"""

    def _build_system_prompt(self) -> str:
        return """你是电信渠道政策计算专家。

【计算原则】
1. 所有计算必须基于文档中的明确数据
2. 必须显示完整的计算过程
3. 注意单位的统一（元/百分比/期数等）
4. 复杂计算要分步骤进行

【标准计算格式】

【计算结果】
XXX元 / XXX% / XXX期

【计算过程】
步骤1：确定计算公式
- 公式：XXX = 基数 × 比例
- 依据：XXX政策第X条

步骤2：获取数值
- 基数：XXX元（来源：XXX）
- 比例：XX%（来源：XXX）

步骤3：代入计算
- XXX × XX% = XXX元

步骤4：汇总（如果有多项）
- 项目1：XXX元
- 项目2：XXX元
- 合计：XXX元

【政策依据】
- 文档：XXX
- 条款：XXX
- 适用条件：XXX

【注意事项】
- 如果文档中没有明确数值，说明"文档中未提供相关数据"
- 如果涉及复杂的阶梯计算，按阶梯分别计算
- 注意计算结果是否符合政策规定的上下限
"""

    def build_prompt(
        self,
        query: str,
        context: List[str],
        chat_history: List[Dict[str, str]] = None,
        calculation_type: str = "general",
        **kwargs
    ) -> str:
        """
        构建计算问题提示词

        Args:
            query: 用户查询
            context: 检索到的文档
            chat_history: 对话历史
            calculation_type: 计算类型（commission/fee/stage/fine）
        """
        parts = []

        # 系统提示词
        parts.append(self.system_prompt)

        # 之前的计算上下文（如果有）
        if chat_history:
            previous_calc = self._extract_previous_calculation(chat_history)
            if previous_calc:
                parts.append(f"【之前的计算】\n{previous_calc}\n")

        # 检索到的文档（重点标注数值）
        if context:
            parts.append(self._format_context_with_numbers(context))

        # 问题分析
        parts.append(self._analyze_calculation(query, calculation_type))

        return "\n\n".join(parts)

    def _extract_previous_calculation(self, history: List[Dict]) -> str:
        """提取之前的计算结果"""
        for msg in reversed(history[-3:]):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if "计算结果" in content or "元" in content:
                    # 提取关键计算信息
                    lines = content.split('\n')
                    for line in lines:
                        if "计算结果" in line or "元" in line:
                            return f"之前计算: {line.strip()}"
        return ""

    def _format_context_with_numbers(self, context: List[str]) -> str:
        """格式化文档，突出数值信息"""
        lines = ["【相关数据】"]

        import re

        for i, doc in enumerate(context[:3], 1):
            doc_text = doc[:800] if len(doc) > 800 else doc

            # 提取并突出数值
            numbers = re.findall(r'\d+(?:\.\d+)?%?|[一二三四五六七八九十百千万]+(?:元|期|倍|分)', doc_text)

            if numbers:
                lines.append(f"\n文档{i}（含关键数据：{', '.join(numbers[:10])}）:")
                lines.append(doc_text)
            else:
                lines.append(f"\n文档{i}: {doc_text}")

        return "\n".join(lines)

    def _analyze_calculation(self, query: str, calc_type: str) -> str:
        """分析计算问题"""
        lines = [f"【计算问题】\n{query}"]

        if calc_type == "commission":
            lines.append("\n【计算类型】分成计算")
            lines.append("需要计算：分成金额/分成比例/分成期数")
        elif calc_type == "fee":
            lines.append("\n【计算类型】费用计算")
            lines.append("需要计算：手续费/激励费/补贴")
        elif calc_type == "stage":
            lines.append("\n【计算类型】阶梯计算")
            lines.append("需要按不同阶梯分别计算后汇总")
        elif calc_type == "fine":
            lines.append("\n【计算类型】处罚计算")
            lines.append("需要注意处罚规则和计算方式")

        # 提取数值
        import re
        numbers = re.findall(r'\d+(?:\.\d+)?', query)
        if numbers:
            lines.append(f"\n【已知数值】{', '.join(numbers)}")

        lines.append("\n请按照【标准计算格式】进行计算。")

        return "\n".join(lines)


class CommissionCalculationPrompt(CalculationPromptTemplate):
    """分成计算专用提示词"""

    def _build_system_prompt(self) -> str:
        base = super()._build_system_prompt()
        return base + """

【分成计算要点】
1. 确认套餐档次（59元以下/59-98元/99-128元/129元以上等）
2. 确认渠道类型（社会渠道/自营厅/校园渠道等）
3. 确认业务场景（新增/存量/校园/政企等）
4. 确认分成比例和期数
5. 计算总分成金额

【常见错误】
- 混淆不同档次的分成比例
- 忽略递延分成的规则
- 忘记考虑适用条件限制
"""


class StageIncentiveCalculationPrompt(CalculationPromptTemplate):
    """阶梯激励计算专用提示词"""

    def _build_system_prompt(self) -> str:
        base = super()._build_system_prompt()
        return base + """

【阶梯激励计算要点】
1. 确认阶梯划分标准（完成量）
2. 确认每个阶梯的激励比例
3. 确认实际完成量
4. 按阶梯分段计算
5. 汇总各阶梯激励金额

【计算公式】
某阶梯激励 = (该阶梯上限 - 上一阶梯上限) × 该阶梯比例
或
某阶梯激励 = 实际完成量 × 该阶梯比例（如果在同一阶梯内）

【示例】
假设阶梯为：
- 0-100户：10元/户
- 101-200户：15元/户
- 200户以上：20元/户

完成150户的计算：
- 前100户：100 × 10 = 1000元
- 101-150户：50 × 15 = 750元
- 合计：1750元
"""


class MultiItemCalculationPrompt(CalculationPromptTemplate):
    """多项目汇总计算专用提示词"""

    def _build_system_prompt(self) -> str:
        base = super()._build_system_prompt()
        return base + """

【多项目汇总计算要点】
1. 分别列出每个项目
2. 单独计算每个项目
3. 汇总所有项目
4. 注意是否有封顶或保底

【计算表格】
建议使用表格形式展示：
| 项目 | 计算公式 | 数值 | 结果 |
|------|----------|------|------|
| 项目1 | XXX | XXX | XXX元 |
| 项目2 | XXX | XXX | XXX元 |
| ... | ... | ... | ... |
| 合计 | - | - | XXX元 |
"""

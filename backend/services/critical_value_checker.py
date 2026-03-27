# -*- coding: utf-8 -*-
"""
关键数值完整性检查模块

专门处理容易被遗漏的数值类型：
- 零值（如0分钟、0GB）
- 小数值（如0.19元/分钟）
- 月度/周期性数值（如X元/月）
- 否定/限制条件（如不支持、不参与）
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class CriticalValueCompletenessChecker:
    """关键数值完整性检查器"""

    # 容易遗漏的数值模式
    EASY_TO_MISS_PATTERNS = {
        "zero_values": [
            r"0\s*分钟", r"0\s*GB", r"0\s*元",  # 零值
            r"0\.19\s*元", r"0\.1\s*元",  # 小数值
        ],
        "periodic_values": [
            r"\d+\.?\d*\s*元\s*[/／]\s*月",  # 月度金额
            r"\d+\.?\d*\s*元\s*[/／]\s*分钟",  # 每分钟费用
            r"\d+\.?\d*\s*元\s*[/／]\s*GB",  # 每GB费用
        ],
        "negative_conditions": [
            r"不支持", r"不参与", r"不能", r"不可",
            r"不包括", r"不含", r"无"
        ],
        "time_codes": [
            r"T\d+-T\d+", r"T\d+至T\d+",  # 时间范围
        ]
    }

    def extract_critical_values(self, text: str) -> Dict[str, List[str]]:
        """
        从文本中提取容易遗漏的关键值

        Args:
            text: 文本内容

        Returns:
            提取到的关键值字典
        """
        result = {
            "zero_values": [],
            "periodic_values": [],
            "negative_conditions": [],
            "time_ranges": []
        }

        # 提取零值和小数值
        for pattern in self.EASY_TO_MISS_PATTERNS["zero_values"]:
            matches = re.findall(pattern, text)
            result["zero_values"].extend(matches)

        # 提取周期性数值
        for pattern in self.EASY_TO_MISS_PATTERNS["periodic_values"]:
            matches = re.findall(pattern, text)
            result["periodic_values"].extend(matches)

        # 提取否定条件
        for pattern in self.EASY_TO_MISS_PATTERNS["negative_conditions"]:
            matches = re.findall(pattern, text)
            result["negative_conditions"].extend(matches)

        # 提取时间范围
        for pattern in self.EASY_TO_MISS_PATTERNS["time_codes"]:
            matches = re.findall(pattern, text)
            result["time_ranges"].extend(matches)

        return result

    def check_completeness(
        self,
        answer: str,
        context: str
    ) -> Tuple[bool, List[str], List[str]]:
        """
        检查答案的关键数值完整性

        Args:
            answer: 生成的答案
            context: 检索上下文

        Returns:
            (是否完整, 缺失的关键值, 找到的关键值)
        """
        # 从上下文中提取关键值
        context_values = self.extract_critical_values(context)
        answer_values = self.extract_critical_values(answer)

        missing = []
        found = []

        # 检查零值和小数值
        for val in context_values["zero_values"]:
            if val in answer:
                found.append(val)
            else:
                missing.append(f"零值/小数值: {val}")

        # 检查周期性数值
        for val in context_values["periodic_values"]:
            if val in answer:
                found.append(val)
            else:
                missing.append(f"周期性数值: {val}")

        # 检查否定条件
        for val in context_values["negative_conditions"]:
            if val in answer:
                found.append(val)
            else:
                missing.append(f"否定条件: {val}")

        # 检查时间范围
        for val in context_values["time_ranges"]:
            # 对时间范围做更宽松的匹配
            val_normalized = val.replace("-", "至").replace("–", "至")
            if val in answer or val_normalized in answer:
                found.append(val)
            else:
                missing.append(f"时间范围: {val}")

        is_complete = len(missing) == 0

        return is_complete, missing, found

    def build_completeness_prompt(
        self,
        context: str,
        query: str
    ) -> str:
        """
        构建关键数值完整性提示词（简化版）

        Args:
            context: 检索上下文
            query: 用户查询

        Returns:
            增强提示词
        """
        # 提取上下文中的关键值
        context_values = self.extract_critical_values(context)

        # 只在有表格对比数据且有关键值时添加提示
        if "## 表格对比数据" not in context:
            return ""

        has_critical = any(context_values.values())
        if not has_critical:
            return ""

        prompt_parts = []

        # 构建简洁的关键值列表
        critical_list = []
        for val in set(context_values["zero_values"][:5]):
            critical_list.append(val)
        for val in set(context_values["periodic_values"][:5]):
            critical_list.append(val)
        for val in set(context_values["negative_conditions"][:3]):
            critical_list.append(val)

        if not critical_list:
            return ""

        prompt_parts.append(f"""
## 数值完整性要求

文档中包含以下关键数值，请务必在答案中准确反映：
{chr(10).join(f'- {v}' for v in critical_list[:8])}

特别注意：
1. **零值很重要**（如"0分钟"）不是省略，必须明确写出
2. **月度金额**要明确是"每/月"，不要只说总额
3. **不支持/不参与**等否定条件要准确表述
""")

        return "\n".join(prompt_parts)

    def highlight_critical_values_in_context(
        self,
        context: str,
        query: str
    ) -> str:
        """
        在上下文中高亮显示关键数值（简化版）

        Args:
            context: 检索上下文
            query: 用户查询

        Returns:
            高亮后的上下文
        """
        # 提取关键值
        context_values = self.extract_critical_values(context)

        # 如果没有关键值，直接返回原上下文
        has_critical_values = any(context_values.values())
        if not has_critical_values:
            return context

        # 只对包含表格数据的上下文添加标注
        if "## 表格对比数据" not in context:
            return context

        highlighted_parts = []
        highlighted_parts.append("\n## 📋 重要提示\n")
        highlighted_parts.append("文档中包含以下容易被遗漏的数值，请务必在答案中包含：\n")

        # 按优先级列出关键值
        priority_values = []

        # 零值和小数值（最高优先级）
        for val in set(context_values["zero_values"]):
            priority_values.append(("⚠️", val))

        # 周期性数值（高优先级）
        for val in set(context_values["periodic_values"]):
            priority_values.append(("💰", val))

        # 否定条件（中优先级）
        for val in set(context_values["negative_conditions"]):
            priority_values.append(("⛔", val))

        # 时间范围（中优先级）
        for val in set(context_values["time_ranges"]):
            priority_values.append(("📅", val))

        # 限制显示数量，避免过多干扰
        for icon, val in priority_values[:10]:
            highlighted_parts.append(f"{icon} {val}")

        highlighted_parts.append("\n" + "-"*40 + "\n")
        highlighted_parts.append(context)

        return "\n".join(highlighted_parts)


# 全局实例
_completeness_checker = None


def get_completeness_checker() -> CriticalValueCompletenessChecker:
    """获取关键数值完整性检查器实例"""
    global _completeness_checker
    if _completeness_checker is None:
        _completeness_checker = CriticalValueCompletenessChecker()
    return _completeness_checker

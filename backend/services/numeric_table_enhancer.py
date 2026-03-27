# -*- coding: utf-8 -*-
"""
数值密集型表格结构化提取模块

专门处理包含大量数值的表格，确保所有数值被准确提取和格式化
"""

import re
import pandas as pd
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class NumericTableEnhancer:
    """数值密集型表格增强器"""

    # 数值模式（包括整数、小数、百分比、金额等）
    NUMERIC_PATTERNS = [
        r"\d+\.?\d*",  # 通用数字
        r"\d+元",  # 金额
        r"\d+%",  # 百分比
        r"\d+\.\d+元",  # 带小数的金额
        r"\d+\.\d+%",  # 带小数的百分比
        r"T\d+",  # 时间代码 (如 T1, T12)
        r"T\d+-T\d+",  # 时间范围 (如 T1-T12)
    ]

    def __init__(self):
        """初始化数值表格增强器"""
        self.stats = {
            "processed_tables": 0,
            "numeric_cells_extracted": 0,
            "enhanced_tables": 0
        }

    def is_numeric_dense_table(self, df: pd.DataFrame) -> bool:
        """
        检测是否为数值密集型表格

        Args:
            df: 表格DataFrame

        Returns:
            是否为数值密集型表格
        """
        if df is None or len(df) == 0:
            return False

        total_cells = len(df) * len(df.columns)
        numeric_cells = 0

        for col in df.columns:
            for val in df[col]:
                if self._is_numeric_value(str(val)):
                    numeric_cells += 1

        # 如果超过50%的单元格是数值，认为是数值密集型表格
        numeric_ratio = numeric_cells / total_cells if total_cells > 0 else 0
        return numeric_ratio > 0.5

    def _is_numeric_value(self, value: str) -> bool:
        """检查一个值是否为数值"""
        value = value.strip()

        # 空值不是数值
        if not value or value.lower() in ["nan", "--", "无", "-"]:
            return False

        # 检查数值模式
        for pattern in self.NUMERIC_PATTERNS:
            if re.fullmatch(pattern, value):
                return True

        # 检查是否为纯数字
        if re.match(r"^\d+\.?\d*$", value):
            return True

        return False

    def extract_numeric_structure(
        self,
        df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        提取表格的数值结构

        Args:
            df: 表格DataFrame

        Returns:
            数值结构字典
        """
        structure = {
            "row_labels": [],
            "column_labels": list(df.columns),
            "numeric_matrix": {},
            "metadata": {
                "rows": len(df),
                "cols": len(df.columns),
                "has_percentages": False,
                "has_amounts": False,
                "has_time_codes": False
            }
        }

        # 找到第一列作为行标签
        first_col = df.columns[0] if len(df.columns) > 0 else None

        for idx, row in df.iterrows():
            if first_col:
                row_label = str(row[first_col]).strip()
                if row_label and row_label not in structure["row_labels"]:
                    structure["row_labels"].append(row_label)

                    # 提取该行的数值
                    row_data = {}
                    for col in df.columns:
                        val = str(row[col]).strip()
                        if self._is_numeric_value(val):
                            row_data[col] = val

                            # 检测数值类型
                            if "%" in val:
                                structure["metadata"]["has_percentages"] = True
                            if "元" in val:
                                structure["metadata"]["has_amounts"] = True
                            if val.startswith("T"):
                                structure["metadata"]["has_time_codes"] = True

                    structure["numeric_matrix"][row_label] = row_data

        self.stats["processed_tables"] += 1
        self.stats["numeric_cells_extracted"] += sum(
            len(v) for v in structure["numeric_matrix"].values()
        )

        return structure

    def format_numeric_table_for_llm(
        self,
        structure: Dict[str, Any],
        max_rows: int = 30
    ) -> str:
        """
        将数值表格结构格式化为LLM友好的文本

        Args:
            structure: 数值结构字典
            max_rows: 最大行数限制

        Returns:
            格式化的文本
        """
        parts = []

        # 添加表格概述
        parts.append("## 数值表格结构化数据")
        parts.append("")
        parts.append("【表格概述】")
        parts.append(f"- 行数: {structure['metadata']['rows']}")
        parts.append(f"- 列数: {structure['metadata']['cols']}")
        parts.append(f"- 有效数据行: {len(structure['row_labels'])}")

        # 添加数值类型标注
        types = []
        if structure['metadata']['has_percentages']:
            types.append("百分比")
        if structure['metadata']['has_amounts']:
            types.append("金额")
        if structure['metadata']['has_time_codes']:
            types.append("时间代码")
        if types:
            parts.append(f"- 数值类型: {', '.join(types)}")

        parts.append("")
        parts.append("【列名列表】")
        for i, col in enumerate(structure['column_labels'], 1):
            parts.append(f"  列{i}: {col}")

        parts.append("")
        parts.append("【数值数据详情】")

        # 按行输出数值数据
        row_count = 0
        for row_label in structure['row_labels'][:max_rows]:
            row_data = structure['numeric_matrix'].get(row_label, {})
            if row_data:
                parts.append(f"行: {row_label}")
                for col, val in row_data.items():
                    parts.append(f"  {col} = {val}")
                row_count += 1

        # 如果有更多行但被截断
        if len(structure['row_labels']) > max_rows:
            parts.append(f"... (还有 {len(structure['row_labels']) - max_rows} 行数据未显示)")

        self.stats["enhanced_tables"] += 1

        return "\n".join(parts)

    def enhance_table_query_result(
        self,
        table_text: str,
        df: pd.DataFrame = None
    ) -> str:
        """
        增强表格查询结果

        Args:
            table_text: 原始表格文本
            df: 表格DataFrame（可选）

        Returns:
            增强后的表格文本
        """
        if df is None:
            return table_text

        # 检查是否为数值密集型表格
        if not self.is_numeric_dense_table(df):
            return table_text

        # 提取数值结构
        structure = self.extract_numeric_structure(df)

        # 格式化为LLM友好的文本
        formatted = self.format_numeric_table_for_llm(structure)

        return f"{table_text}\n\n{formatted}"

    def extract_all_numeric_values(
        self,
        text: str
    ) -> List[Dict[str, Any]]:
        """
        从文本中提取所有数值及其上下文

        Args:
            text: 文本内容

        Returns:
            数值列表，每个数值包含类型和原始文本
        """
        results = []

        # 提取金额
        amounts = re.findall(r"(\d+\.?\d*)\s*元", text)
        for amount in amounts:
            results.append({"type": "amount", "value": amount, "unit": "元"})

        # 提取百分比
        percentages = re.findall(r"(\d+\.?\d*)\s*%", text)
        for pct in percentages:
            results.append({"type": "percentage", "value": pct, "unit": "%"})

        # 提取时间代码
        time_codes = re.findall(r"(T\d+(?:[-~到]T\d+)?)", text)
        for tc in time_codes:
            results.append({"type": "time_code", "value": tc, "unit": ""})

        # 提取纯数字（可能是数量、天数等）
        numbers = re.findall(r"\d+", text)
        for num in numbers:
            # 避免重复提取
            if not any(r["value"] == num for r in results):
                results.append({"type": "number", "value": num, "unit": ""})

        return results

    def validate_numeric_completeness(
        self,
        answer: str,
        context: str
    ) -> Dict[str, Any]:
        """
        验证答案中的数值完整性

        Args:
            answer: 生成的答案
            context: 检索上下文

        Returns:
            验证结果
        """
        result = {
            "is_complete": True,
            "missing_values": [],
            "found_values": [],
            "context_numeric_count": 0,
            "answer_numeric_count": 0
        }

        # 提取上下文中的数值
        context_values = self.extract_all_numeric_values(context)
        result["context_numeric_count"] = len(context_values)

        # 提取答案中的数值
        answer_values = self.extract_all_numeric_values(answer)
        result["answer_numeric_count"] = len(answer_values)

        # 对于重要的数值（金额、百分比），检查是否都在答案中
        important_values = [
            v for v in context_values
            if v["type"] in ["amount", "percentage"]
        ]

        for ctx_val in important_values:
            found = False
            for ans_val in answer_values:
                if ctx_val["value"] == ans_val["value"]:
                    found = True
                    result["found_values"].append(ctx_val)
                    break

            if not found:
                result["missing_values"].append(ctx_val)

        # 如果有重要数值缺失，标记为不完整
        if result["missing_values"]:
            result["is_complete"] = False

        return result

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self.stats.copy()


# 全局实例
_numeric_table_enhancer = None


def get_numeric_table_enhancer() -> NumericTableEnhancer:
    """获取数值表格增强器实例"""
    global _numeric_table_enhancer
    if _numeric_table_enhancer is None:
        _numeric_table_enhancer = NumericTableEnhancer()
    return _numeric_table_enhancer

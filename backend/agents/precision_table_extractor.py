"""
精确表格数据提取器
专门解决转置表格中数值提取不准确的问题

核心功能：
1. 精确列名识别 - 区分层级列名
2. 数值单位保留 - 确保提取时保留单位
3. 多维度数据提取 - 支持条件筛选的数值提取
4. 数据完整性验证 - 确保提取的数值符合表格结构
"""

import re
import logging
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExtractedValue:
    """提取的数值"""
    value: str
    unit: str
    row_label: str
    column_label: str
    context: Dict[str, Any]
    confidence: float


@dataclass
class TableExtractionResult:
    """表格提取结果"""
    is_transposed: bool
    row_labels: List[str]
    column_labels: List[str]
    data_matrix: Dict[str, Dict[str, str]]  # {row_label: {col_label: value}}
    metadata: Dict[str, Any]


class PrecisionTableExtractor:
    """精确表格数据提取器"""

    # 数值模式（用于识别表格中的数值）
    NUMERIC_PATTERNS = [
        r'\d+(?:\.\d+)?元',  # 金额
        r'\d+(?:\.\d+)?%?',  # 百分比或纯数字
        r'\d+(?:\.\d+)?倍',  # 倍数
        r'T\d+(?:\s*[-~到]\s*T\d+)?',  # 时间范围
        r'\d+(?:\.\d+)?个月?',  # 月数
        r'\d+(?:\.\d+)?年?',  # 年数
    ]

    # 列名层级指示词
    HIERARCHY_INDICATORS = [
        ('区域服务商', ['区域服务商', '区域', '属地']),
        ('非区域服务商', ['非区域', '委托厅', '全业务', '自营', 'Shopping']),
        ('渠道类型', ['渠道', '校园', '微格', '社会']),
        ('套餐档位', ['129元', '59元', '69元', '79元', '39元', '99元', '149元', '189元']),
        ('星级', ['6星C', '6星B', '5星', '4星', '3星']),
    ]

    def __init__(self):
        """初始化精确表格提取器"""
        self._table_cache = {}

    def analyze_table_structure(self, df: pd.DataFrame) -> TableExtractionResult:
        """
        分析表格结构

        Args:
            df: 表格DataFrame

        Returns:
            表格提取结果
        """
        # 检测是否为转置表格
        is_transposed = self._detect_transposed_table(df)

        if is_transposed:
            return self._analyze_transposed_table(df)
        else:
            return self._analyze_standard_table(df)

    def _detect_transposed_table(self, df: pd.DataFrame) -> bool:
        """
        检测是否为转置表格

        转置表格特征：
        1. 列名包含分类/对比词汇
        2. 第一列是指标/属性名称
        3. 多个数据列代表不同类别
        """
        if len(df.columns) < 3:
            return False

        # 检查列名
        column_text = " ".join([str(col) for col in df.columns])

        # 转置表格特征词
        transposed_keywords = [
            "区域服务商", "非区域", "委托厅", "全业务",
            "服务商", "渠道", "校园", "自营", "Shopping",
            "129元", "套餐档位", "服补", "对比", "倍数",
            "比例", "时间", "发放", "门槛", "星级"
        ]

        keyword_count = sum(1 for kw in transposed_keywords if kw in column_text)

        # 检查第一列是否是指标名称
        if len(df) > 0:
            first_col_values = [str(val) for val in df.iloc[:, 0].dropna()]
            metric_indicators = ["倍数", "比例", "时间", "发放", "档位", "门槛", "金额", "星级", "费用", "分成", "激励"]
            has_metrics = any(any(kw in val for kw in metric_indicators) for val in first_col_values)

            if has_metrics and keyword_count >= 1:
                return True

        return keyword_count >= 2

    def _analyze_transposed_table(self, df: pd.DataFrame) -> TableExtractionResult:
        """
        分析转置表格结构

        关键改进：
        1. 准确识别列名层级
        2. 提取完整的列名（不截断）
        3. 保留数值单位
        """
        # 获取所有列名
        raw_columns = [str(col) for col in df.columns]

        # 分析列名层级
        column_labels = self._parse_column_hierarchy(raw_columns)

        # 获取行标签（第一列）
        first_col = df.columns[0] if len(df.columns) > 0 else None
        row_labels = []

        if first_col:
            seen_labels = set()
            for idx, row in df.iterrows():
                label = str(row[first_col]).strip()
                if label and label != "nan" and label not in seen_labels:
                    row_labels.append(label)
                    seen_labels.add(label)

        # 提取数据矩阵
        data_matrix = {}

        for row_label in row_labels:
            data_matrix[row_label] = {}

            # 找到所有匹配该行标签的行
            matching_rows = df[df[first_col] == row_label]

            if len(matching_rows) == 0:
                continue

            # 使用第一个匹配行
            row = matching_rows.iloc[0]

            # 提取每列的值
            for raw_col, parsed_label in zip(raw_columns, column_labels):
                if raw_col == first_col:
                    continue

                value = str(row.get(raw_col, ""))
                if value and value not in ["nan", "", "--", "-"]:
                    # 保留完整值（包括单位）
                    data_matrix[row_label][parsed_label] = value

        return TableExtractionResult(
            is_transposed=True,
            row_labels=row_labels,
            column_labels=column_labels,
            data_matrix=data_matrix,
            metadata={
                "raw_columns": raw_columns,
                "first_column": str(first_col) if first_col else None,
                "shape": df.shape
            }
        )

    def _parse_column_hierarchy(self, raw_columns: List[str]) -> List[str]:
        """
        解析列名层级，生成简化的列标签

        这个方法非常关键 - 它决定了数值提取的准确性
        """
        parsed_labels = []

        for col in raw_columns:
            col_str = str(col).strip()

            # 第一列通常是指标名称
            if not col_str or col_str == "nan" or "Unnamed" in col_str:
                if len(parsed_labels) == 0:
                    parsed_labels.append("指标名称")
                else:
                    parsed_labels.append(f"列{len(parsed_labels)}")
                continue

            # 根据层级指示词分类
            label = self._categorize_column(col_str)
            parsed_labels.append(label)

        return parsed_labels

    def _categorize_column(self, column_name: str) -> str:
        """
        对列名进行分类

        这是核心方法 - 准确的列名分类是精确提取的前提
        """
        # 优先检查区域服务商相关
        if "区域服务商" in column_name or ("区域" in column_name and "渠道" in column_name):
            if "非区域" not in column_name:
                return "区域服务商"

        # 检查非区域服务商
        if any(kw in column_name for kw in ["委托厅", "全业务", "自营", "Shopping", "非区域"]):
            return "非区域服务商"

        # 检查套餐档位
        for price in ["189元", "149元", "129元", "99元", "79元", "69元", "59元", "39元", "29元"]:
            if price in column_name:
                # 进一步区分类别
                if "区域服务商" in column_name or "属地" in column_name:
                    return f"{price}_区域服务商"
                elif any(kw in column_name for kw in ["委托", "全业务", "自营"]):
                    return f"{price}_非区域"
                else:
                    return price

        # 检查星级
        if "星" in column_name:
            return column_name[:10]  # 保留星级完整名称

        # 默认返回简化的列名
        # 提取关键部分，去除冗余
        simplified = column_name
        # 移除常见的前缀
        for prefix in ["广东移动", "中国移动", "全省", "统一"]:
            if simplified.startswith(prefix):
                simplified = simplified[len(prefix):].strip()
        # 移除常见的后缀
        for suffix in ["(不含校园)", "(不含微格)"]:
            if simplified.endswith(suffix):
                simplified = simplified[:-len(suffix)].strip()

        return simplified[:20] if simplified else column_name[:20]

    def _analyze_standard_table(self, df: pd.DataFrame) -> TableExtractionResult:
        """分析标准表格（非转置）"""
        column_labels = [str(col) for col in df.columns]
        row_labels = []

        # 使用第一列的值作为行标签
        if len(df.columns) > 0:
            first_col = df.columns[0]
            row_labels = [str(val) for val in df[first_col].unique() if str(val) != "nan"]

        # 构建数据矩阵
        data_matrix = {}

        for _, row in df.iterrows():
            row_label = str(row[df.columns[0]]) if len(df.columns) > 0 else f"行{_}"
            data_matrix[row_label] = {}

            for col in df.columns[1:]:
                val = str(row[col])
                if val and val not in ["nan", "", "--"]:
                    data_matrix[row_label][str(col)] = val

        return TableExtractionResult(
            is_transposed=False,
            row_labels=row_labels,
            column_labels=column_labels,
            data_matrix=data_matrix,
            metadata={"shape": df.shape}
        )

    def extract_value_by_condition(
        self,
        table_result: TableExtractionResult,
        row_keywords: List[str],
        column_keywords: List[str]
    ) -> List[ExtractedValue]:
        """
        根据行和列关键词提取数值

        这是核心方法 - 实现精确的条件匹配

        Args:
            table_result: 表格分析结果
            row_keywords: 行关键词列表
            column_keywords: 列关键词列表

        Returns:
            提取的数值列表
        """
        results = []

        # 匹配行
        matched_rows = self._match_rows(table_result.row_labels, row_keywords)

        # 匹配列
        matched_cols = self._match_columns(table_result.column_labels, column_keywords)

        # 提取数值
        for row_label in matched_rows:
            if row_label not in table_result.data_matrix:
                continue

            for col_label in matched_cols:
                if col_label in table_result.data_matrix[row_label]:
                    value = table_result.data_matrix[row_label][col_label]

                    # 提取单位和数值
                    unit = self._extract_unit(value)
                    confidence = self._calculate_confidence(row_label, col_label, row_keywords, column_keywords)

                    results.append(ExtractedValue(
                        value=value,
                        unit=unit,
                        row_label=row_label,
                        column_label=col_label,
                        context={
                            "matched_row_keywords": [kw for kw in row_keywords if kw in row_label],
                            "matched_col_keywords": [kw for kw in column_keywords if kw in col_label],
                        },
                        confidence=confidence
                    ))

        # 按置信度排序
        results.sort(key=lambda x: x.confidence, reverse=True)

        return results

    def _match_rows(self, row_labels: List[str], keywords: List[str]) -> List[str]:
        """匹配行标签"""
        matched = []

        for label in row_labels:
            label_lower = label.lower()

            # 计算匹配分数
            score = 0
            for kw in keywords:
                if kw.lower() in label_lower:
                    # 完全匹配给予高分
                    if kw.lower() == label_lower:
                        score += 10
                    # 部分匹配
                    else:
                        score += 5

            # 匹配数字
            for kw in keywords:
                numbers = re.findall(r'\d+(?:\.\d+)?', str(kw))
                for num in numbers:
                    if num in label:
                        score += 3

            if score > 0:
                matched.append((label, score))

        # 按分数排序
        matched.sort(key=lambda x: x[1], reverse=True)
        return [label for label, _ in matched]

    def _match_columns(self, column_labels: List[str], keywords: List[str]) -> List[str]:
        """匹配列标签"""
        matched = []

        for label in column_labels:
            label_lower = label.lower()

            # 计算匹配分数
            score = 0
            for kw in keywords:
                kw_lower = kw.lower()

                # 完全匹配
                if kw_lower == label_lower:
                    score += 10
                # 包含匹配
                elif kw_lower in label_lower:
                    score += 5
                # 反向包含（列名包含关键词）
                elif label_lower in kw_lower:
                    score += 3

            # 特殊处理：区域服务商/非区域
            if any(kw in keywords for kw in ["区域服务商", "服务商"]):
                if "区域服务商" in label or ("区域" in label and "非区域" not in label):
                    score += 8

            if any(kw in keywords for kw in ["非区域", "委托厅", "全业务"]):
                if any(kw in label for kw in ["委托厅", "全业务", "自营", "非区域", "Shopping"]):
                    score += 8

            if score > 0:
                matched.append((label, score))

        # 按分数排序
        matched.sort(key=lambda x: x[1], reverse=True)
        return [label for label, _ in matched]

    def _extract_unit(self, value: str) -> str:
        """提取数值单位"""
        # 常见单位
        units = ["元", "%", "倍", "个月", "年", "GB", "MB", "天", "次", "笔", "户"]

        for unit in units:
            if unit in value:
                return unit

        return ""

    def _calculate_confidence(
        self,
        row_label: str,
        col_label: str,
        row_keywords: List[str],
        col_keywords: List[str]
    ) -> float:
        """计算匹配置信度"""
        confidence = 0.0

        # 行匹配分数
        row_score = 0
        for kw in row_keywords:
            if kw.lower() in row_label.lower():
                if kw.lower() == row_label.lower():
                    row_score += 1.0
                else:
                    row_score += 0.5

        # 列匹配分数
        col_score = 0
        for kw in col_keywords:
            if kw.lower() in col_label.lower():
                if kw.lower() == col_label.lower():
                    col_score += 1.0
                else:
                    col_score += 0.5

        # 综合置信度
        confidence = (row_score + col_score) / 2

        return min(confidence, 1.0)

    def format_for_llm(self, table_result: TableExtractionResult, query: str = "") -> str:
        """
        为LLM格式化表格数据

        关键改进：
        1. 清晰的数据结构说明
        2. 完整的数值展示（带单位）
        3. 高亮关键数据
        """
        lines = []

        # 标题
        lines.append("## 表格精确提取数据")
        lines.append("")

        # 数据结构说明
        if table_result.is_transposed:
            lines.append("【表格结构：转置对比表】")
            lines.append("- 第一列：指标/属性名称")
            lines.append("- 后续列：不同类别对应的数值")
            lines.append("")
        else:
            lines.append("【表格结构：标准数据表】")
            lines.append("")

        # 列名对应关系（重要！）
        lines.append("【列名说明】")
        if hasattr(table_result, 'metadata') and 'raw_columns' in table_result.metadata:
            raw_cols = table_result.metadata.get('raw_columns', [])
            for i, (parsed, raw) in enumerate(zip(table_result.column_labels, raw_cols)):
                lines.append(f"- 列{i+1}: {parsed} (原列名: {raw[:40]}...)")
        else:
            for i, label in enumerate(table_result.column_labels):
                lines.append(f"- 列{i+1}: {label}")
        lines.append("")

        # 数据详情
        lines.append("【数据详情】")
        lines.append("")

        for row_label in table_result.row_labels[:20]:  # 限制行数
            if row_label not in table_result.data_matrix:
                continue

            row_data = table_result.data_matrix[row_label]
            if not row_data:
                continue

            # 构建数据行
            parts = [f"指标: {row_label}"]

            for col_label in table_result.column_labels[1:]:  # 跳过第一列
                if col_label in row_data:
                    value = row_data[col_label]
                    parts.append(f"{col_label}={value}")

            if len(parts) > 1:
                lines.append(" | ".join(parts))

        return "\n".join(lines)

    def extract_all_numeric_values(
        self,
        table_result: TableExtractionResult
    ) -> Dict[str, List[Tuple[str, str]]]:
        """
        提取所有数值

        Returns:
            {指标名称: [(列名, 数值), ...]}
        """
        result = {}

        for row_label in table_result.row_labels:
            if row_label not in table_result.data_matrix:
                continue

            row_data = table_result.data_matrix[row_label]
            values = []

            for col_label, value in row_data.items():
                # 检查是否为数值
                if self._is_numeric_value(value):
                    values.append((col_label, value))

            if values:
                result[row_label] = values

        return result

    def _is_numeric_value(self, value: str) -> bool:
        """检查是否为数值"""
        # 检查是否匹配数值模式
        for pattern in self.NUMERIC_PATTERNS:
            if re.search(pattern, value):
                return True

        # 检查是否为纯数字
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            pass

        return False


# 单例
_extractor = None


def get_precision_extractor() -> PrecisionTableExtractor:
    """获取精确表格提取器实例"""
    global _extractor
    if _extractor is None:
        _extractor = PrecisionTableExtractor()
    return _extractor

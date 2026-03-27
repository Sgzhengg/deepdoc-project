# -*- coding: utf-8 -*-
"""
通用表格解析模块

自动识别表格类型、解析表格数据、支持表格查询
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TableType(Enum):
    """表格类型枚举"""
    UNKNOWN = "unknown"
    PACKAGE_COMPARISON = "package_comparison"  # 套餐对比表
    FEE_CALCULATION = "fee_calculation"  # 费用计算表
    INCENTIVE_PLAN = "incentive_plan"  # 激励方案表
    SERVICE_RULE = "service_rule"  # 服务规则表
    CHANNEL_POLICY = "channel_policy"  # 渠道政策表


@dataclass
class TableColumn:
    """表格列定义"""
    name: str
    data_type: str = "string"  # string, number, currency, percentage
    description: str = ""


@dataclass
class TableRow:
    """表格行数据"""
    data: Dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""


@dataclass
class ParsedTable:
    """解析后的表格"""
    table_type: TableType = TableType.UNKNOWN
    columns: List[TableColumn] = field(default_factory=list)
    rows: List[TableRow] = field(default_factory=list)
    raw_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def query(self, condition: str, target_column: str = None) -> List[Any]:
        """
        查询表格数据

        Args:
            condition: 查询条件（支持简单的值匹配）
            target_column: 目标列名，如果为None则返回整行

        Returns:
            查询结果列表
        """
        results = []
        for row in self.rows:
            # 检查条件是否匹配
            condition_met = False
            for value in row.data.values():
                if condition.lower() in str(value).lower():
                    condition_met = True
                    break

            if condition_met:
                if target_column:
                    results.append(row.data.get(target_column))
                else:
                    results.append(row.data)

        return results

    def get_column_values(self, column_name: str) -> List[Any]:
        """获取指定列的所有值"""
        return [row.data.get(column_name) for row in self.rows if column_name in row.data]

    def to_markdown(self) -> str:
        """转换为Markdown表格格式"""
        if not self.columns or not self.rows:
            return "空表格"

        lines = []

        # 表头
        headers = [col.name for col in self.columns]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # 数据行
        for row in self.rows[:50]:  # 限制最多50行
            cells = [str(row.data.get(col.name, "")) for col in self.columns]
            lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'type': self.table_type.value,
            'columns': [col.name for col in self.columns],
            'rows': [row.data for row in self.rows],
            'row_count': len(self.rows)
        }


class UniversalTableParser:
    """通用表格解析器"""

    # 表格类型特征关键词
    TABLE_TYPE_KEYWORDS = {
        TableType.PACKAGE_COMPARISON: {
            'primary': ['套餐', '价格', '资费', '流量', '通话', '方案ID'],
            'secondary': ['潮玩青春卡', '全家享', '融合套餐', '对比']
        },
        TableType.FEE_CALCULATION: {
            'primary': ['费用', '计算', 'T+', '合计', '分成', '激励'],
            'secondary': ['首充', '实名', '套餐分成', '达量']
        },
        TableType.INCENTIVE_PLAN: {
            'primary': ['星级', '门槛', '激励', '达量', '完成'],
            'secondary': ['考核', '标准', '达标']
        },
        TableType.SERVICE_RULE: {
            'primary': ['规则', '条件', '要求', '标准', '说明'],
            'secondary': ['办理', '使用', '享受', '适用']
        },
        TableType.CHANNEL_POLICY: {
            'primary': ['渠道', '政策', '范围', '类型'],
            'secondary': ['区域', '服务商', '厅店', '校园']
        }
    }

    # 列名模式识别
    COLUMN_PATTERNS = {
        'package_name': r'(?:套餐名称|方案|产品)',
        'price': r'(?:价格|资费|月租|费用)',
        'data': r'(?:流量|通话|分钟|GB|MB)',
        'fee': r'(?:手续费|分成|激励)',
        'channel': r'(?:渠道|门店|区域)',
        'incentive': r'(?:星级|门槛|达量)'
    }

    def __init__(self, config: Dict[str, Any] = None):
        """初始化解析器"""
        self.config = config or {}
        self.parse_cache = {}
        # Phase 2: 时间周期缓存
        self.time_period_cache = {}

    def parse_from_text(
        self,
        table_text: str,
        source_doc: str = ""
    ) -> ParsedTable:
        """
        从文本解析表格

        Args:
            table_text: 表格文本内容
            source_doc: 来源文档

        Returns:
            解析后的表格对象
        """
        # 检测表格类型
        table_type = self._identify_table_type(table_text)

        # 提取表格行
        rows_text = self._extract_rows(table_text)

        # 解析表头
        columns = self._parse_headers(rows_text[0] if rows_text else "", table_type)

        # 解析数据行
        rows = []
        for row_text in rows_text[1:] if len(rows_text) > 1 else []:  # 跳过表头
            row = self._parse_row(row_text, columns)
            if row.data:  # 只保留非空行
                rows.append(row)

        return ParsedTable(
            table_type=table_type,
            columns=columns,
            rows=rows,
            raw_text=table_text,
            metadata={'source_doc': source_doc}
        )

    def _identify_table_type(self, text: str) -> TableType:
        """识别表格类型"""
        scores = {}

        for table_type, keywords in self.TABLE_TYPE_KEYWORDS.items():
            primary_score = sum(1 for kw in keywords['primary'] if kw in text)
            secondary_score = sum(1 for kw in keywords['secondary'] if kw in text) * 0.5
            scores[table_type] = primary_score + secondary_score

        if not scores or max(scores.values()) == 0:
            return TableType.UNKNOWN

        # 返回得分最高的类型
        return max(scores, key=scores.get)

    def _extract_rows(self, text: str) -> List[str]:
        """提取表格行"""
        # 按行分割
        lines = text.strip().split('\n')

        # 过滤空行和明显不是表格内容的行
        rows = []
        for line in lines:
            line = line.strip()
            if line and len(line) > 3:  # 至少3个字符
                # 检测是否包含表格特征（如分隔符或多个连续字符）
                if self._is_table_row(line):
                    rows.append(line)

        return rows

    def _is_table_row(self, line: str) -> bool:
        """判断是否为表格行"""
        # 检查常见的表格行特征
        indicators = [
            '|' in line,  # Markdown表格
            '\t' in line,  # CSV表格
            '：' in line,  # 中文冒号分隔
            re.search(r'\d+[元%]', line),  # 包含数值单位
        ]
        return any(indicators)

    def _parse_headers(self, header_text: str, table_type: TableType) -> List[TableColumn]:
        """解析表头"""
        columns = []

        # 尝试不同的分隔符
        delimiters = ['|', '\t', '：', ';']

        for delimiter in delimiters:
            if delimiter in header_text:
                parts = header_text.split(delimiter)
                parts = [p.strip() for p in parts if p.strip()]

                if len(parts) >= 2:  # 至少2列才认为是有效表头
                    for i, part in enumerate(parts):
                        col_type = self._infer_column_type(part, table_type)
                        columns.append(TableColumn(
                            name=part,
                            data_type=col_type
                        ))
                    break

        # 如果没有找到明确的分隔符，尝试按位置解析
        if not columns:
            # 使用默认列名
            columns = [
                TableColumn(name=f"列{i+1}", data_type="string")
                for i in range(5)  # 默认5列
            ]

        return columns

    def _infer_column_type(self, header: str, table_type: TableType) -> str:
        """推断列数据类型"""
        header_lower = header.lower()

        # 数值类型
        if any(kw in header_lower for kw in ['价格', '资费', '费用', '分成', '激励', '金额']):
            return "currency"

        if any(kw in header_lower for kw in ['数量', '分钟', '次数', '个数', '人数']):
            return "number"

        if any(kw in header_lower for kw in ['流量', 'GB', 'MB', 'KB']):
            return "data_size"

        if any(kw in header_lower for kw in ['比例', '率', '%', '折扣']):
            return "percentage"

        # 默认字符串类型
        return "string"

    def _parse_row(self, row_text: str, columns: List[TableColumn]) -> TableRow:
        """解析数据行"""
        data = {}

        # 尝试与列对齐
        if columns:
            # 查找最合适的分隔符
            delimiters = ['|', '\t', '：', ';']
            best_delimiter = None
            best_parts_count = 0

            for delimiter in delimiters:
                if delimiter in row_text:
                    parts = row_text.split(delimiter)
                    parts = [p.strip() for p in parts if p.strip()]
                    if len(parts) > best_parts_count:
                        best_delimiter = delimiter
                        best_parts_count = len(parts)

            if best_delimiter:
                parts = row_text.split(best_delimiter)
                parts = [p.strip() for p in parts if p.strip()]
            else:
                # 没有明确分隔符，尝试按列宽解析（简化处理）
                parts = [row_text]  # 整行作为一列

            for i, column in enumerate(columns):
                if i < len(parts):
                    value = parts[i].strip()
                    data[column.name] = self._convert_value(value, column.data_type)
        else:
            data = {"raw": row_text}

        return TableRow(data=data, raw_text=row_text)

    def _convert_value(self, value: str, data_type: str) -> Any:
        """转换值类型"""
        value = value.strip()
        if not value:
            return None

        try:
            if data_type == "currency":
                # 提取数值
                numbers = re.findall(r'[\d.]+', value)
                if numbers:
                    return float(numbers[0])
            elif data_type == "number":
                return int(re.findall(r'\d+', value)[0]) if re.findall(r'\d+', value) else 0
            elif data_type == "percentage":
                return float(re.findall(r'[\d.]+', value)[0]) / 100 if '%' in value else float(value)
        except (IndexError, ValueError):
            pass

        return value

    def format_for_prompt(
        self,
        tables: List[ParsedTable],
        max_tables: int = 3
    ) -> str:
        """
        将表格格式化为提示词文本

        Phase 3.1 增强：包含提取的时间周期信息

        Args:
            tables: 解析后的表格列表
            max_tables: 最多包含的表格数量

        Returns:
            格式化的表格文本
        """
        if not tables:
            return ""

        lines = ["## 检索到的表格数据"]

        # Phase 3.1: 提取并显示时间周期信息
        time_periods = self.extract_time_periods(tables)
        if time_periods:
            lines.append("\n**时间周期规则**:")
            for tp in time_periods:
                if tp.get('type') == 'service_incentive_t_range':
                    # 服务运营激励特殊格式
                    start = tp.get('start_month')
                    end = tp.get('end_month')
                    normalized = tp.get('normalized', f'T+{start}至T+{end}')
                    percentages = tp.get('percentages', {})
                    lines.append(f"- 发放周期: {normalized}")
                    if percentages:
                        if 'non_regional' in percentages:
                            lines.append(f"  - 非区域服务商: {percentages['non_regional']}%")
                        if 'regional' in percentages:
                            lines.append(f"  - 区域服务商: {percentages['regional']}%")
                elif 'start_month' in tp and 'end_month' in tp:
                    start = tp.get('start_month')
                    end = tp.get('end_month')
                    percentage = tp.get('percentage', '')
                    lines.append(f"- T+{start}至T+{end}: {percentage}%")

        for i, table in enumerate(tables[:max_tables]):
            lines.append(f"\n### 表格 {i+1}: {table.metadata.get('source_doc', '')}")
            lines.append(f"**类型**: {table.table_type.value}")

            if table.table_type != TableType.UNKNOWN:
                # 添加关键数据摘要
                lines.append("\n**关键数据**:")

                # 获取前几行数据作为示例
                for row in table.rows[:5]:
                    if row.data:
                        items = [f"{k}: {v}" for k, v in row.data.items() if v and v != ""]
                        if items:
                            lines.append("- " + ", ".join(items[:3]))  # 最多显示3项

        return "\n".join(lines)

    def query_table(
        self,
        tables: List[ParsedTable],
        query: str,
        condition: str = None
    ) -> Dict[str, Any]:
        """
        从表格中查询信息

        Args:
            tables: 表格列表
            query: 查询语句
            condition: 查询条件

        Returns:
            查询结果字典
        """
        results = {
            'query': query,
            'found_tables': [],
            'data': []
        }

        for table in tables:
            # 简单的查询逻辑：如果查询条件在表格中出现，则返回相关行
            if condition and condition.lower() in table.raw_text.lower():
                table_results = table.query(condition)
                if table_results:
                    results['found_tables'].append(table.table_type.value)
                    results['data'].extend(table_results)
            elif not condition:
                # 没有条件，返回整个表格的摘要
                results['found_tables'].append(table.table_type.value)
                results['data'].append(table.to_dict())

        return results

    # ========== Phase 2 新增方法: 时间周期解析 ==========

    def extract_time_periods(
        self,
        tables: List[ParsedTable]
    ) -> List[Dict[str, Any]]:
        """
        从表格中提取时间周期信息（Phase 2 新增）

        用于识别激励发放周期等时间相关业务规则

        Args:
            tables: 解析后的表格列表

        Returns:
            时间周期信息列表
        """
        periods = []

        for table in tables:
            # 检查是否为激励相关表格
            if table.table_type in [TableType.INCENTIVE_PLAN, TableType.FEE_CALCULATION]:
                # 从表格内容中提取时间周期
                table_periods = self._extract_periods_from_table(table)
                periods.extend(table_periods)

        return periods

    def _extract_periods_from_table(
        self,
        table: ParsedTable
    ) -> List[Dict[str, Any]]:
        """
        从单个表格中提取时间周期

        DeepSeek 分析后增强（Phase 3.1）：
        - 支持 T3-T12 月格式（不带+号）
        - 从表格不同列中提取渠道特定的百分比
        """
        periods = []

        # 在表格原始文本中查找时间周期模式
        text = table.raw_text

        # ========== DeepSeek 建议的新模式 ==========

        # 模式0（新增）: Tn-Tm月格式（服务运营激励表格）
        # 匹配 "T3-T12月" 或 "费用发放周期 T3-T12月"
        pattern0 = r'T(\d+)\s*[-至~]\s*T(\d+)\s*月'
        matches0 = re.finditer(pattern0, text)
        for match in matches0:
            start_month = int(match.group(1))
            end_month = int(match.group(2))

            # 提取关联的百分比信息
            percentages = self._extract_percentages_from_context(text, match)

            period_info = {
                'type': 'service_incentive_t_range',
                'start_month': start_month,
                'end_month': end_month,
                'duration': end_month - start_month + 1,
                'source': table.metadata.get('source_doc', ''),
                'description': f"T{start_month}-T{end_month}月",
                'normalized': f"T+{start_month}至T+{end_month}",
                'percentages': percentages,
            }

            logger.info(f"📊 [DeepSeek] 提取服务运营激励周期: T+{start_month}至T+{end_month}, 比例: {percentages}")
            periods.append(period_info)

        # 模式1: T+n 至 T+m 各发放X%
        pattern1 = r'T\+(\d+)\s*至\s*T\+(\d+).*?各\s*发放\s*(\d+)%'
        matches1 = re.finditer(pattern1, text)
        for match in matches1:
            periods.append({
                'type': 't_range_percentage',
                'start_month': int(match.group(1)),
                'end_month': int(match.group(2)),
                'percentage': int(match.group(3)),
                'duration': int(match.group(2)) - int(match.group(1)) + 1,
                'source': table.metadata.get('source_doc', ''),
                'description': match.group(0)
            })

        # 模式2: 连续N个月
        pattern2 = r'连续\s*(\d+)\s*个月.*?发放\s*(\d+)%'
        matches2 = re.finditer(pattern2, text)
        for match in matches2:
            periods.append({
                'type': 'consecutive_months',
                'months': int(match.group(1)),
                'percentage': int(match.group(2)),
                'source': table.metadata.get('source_doc', ''),
                'description': match.group(0)
            })

        # 模式3: T+n月起开始发放
        pattern3 = r'T\+(\d+)\s*月.*?开始.*?发放'
        matches3 = re.finditer(pattern3, text)
        for match in matches3:
            periods.append({
                'type': 'start_month',
                'start_month': int(match.group(1)),
                'source': table.metadata.get('source_doc', ''),
                'description': match.group(0)
            })

        return periods

    def _extract_percentages_from_context(
        self,
        text: str,
        period_match
    ) -> Dict[str, int]:
        """
        DeepSeek 建议：从表格上下文中提取渠道特定的百分比

        查找模式：
        - "15%" 和 "25%" 分别对应非区域服务商和区域服务商
        - "1.5倍" 和 "2.5倍" 作为额外的识别标识
        """
        percentages = {}

        # 查找匹配位置附近的文本（前后200字符）
        match_pos = period_match.start()
        context_start = max(0, match_pos - 200)
        context_end = min(len(text), match_pos + 200)
        context = text[context_start:context_end]

        # 提取所有百分比
        all_percentages = re.findall(r'(\d+)%', context)

        # 检查是否有 15% 和 25% 的组合（服务运营激励的典型模式）
        if '15' in all_percentages and '25' in all_percentages:
            percentages['non_regional'] = 15  # 非区域服务商
            percentages['regional'] = 25      # 区域服务商
            logger.info(f"💰 [DeepSeek] 检测到服务运营激励比例: 非区域15%, 区域25%")
        elif len(all_percentages) == 1:
            # 单一百分比
            percentages['default'] = int(all_percentages[0])
        elif len(all_percentages) >= 2:
            # 多个百分比，按顺序分配
            percentages['channel_1'] = int(all_percentages[0])
            percentages['channel_2'] = int(all_percentages[1])

        # 检查倍数标识（1.5倍/2.5倍）
        if '1.5倍' in context and '2.5倍' in context:
            percentages['multiplier_non_regional'] = 1.5
            percentages['multiplier_regional'] = 2.5
            logger.info(f"📊 [DeepSeek] 检测到倍数: 非区域1.5倍, 区域2.5倍")

        return percentages

    def verify_time_period_answer(
        self,
        answer: str,
        tables: List[ParsedTable]
    ) -> Tuple[bool, str]:
        """
        验证答案中的时间周期是否与表格数据一致（Phase 2 新增）

        Args:
            answer: 系统答案
            tables: 相关表格

        Returns:
            (是否准确, 错误描述)
        """
        # 从表格中提取正确的时间周期
        correct_periods = self.extract_time_periods(tables)

        # 从答案中提取时间周期
        answer_periods = self._extract_periods_from_text(answer)

        # 比较验证
        for correct_period in correct_periods:
            for answer_period in answer_periods:
                # 检查T+n至T+m格式
                if (correct_period.get('type') == 't_range_percentage' and
                    answer_period.get('type') == 't_range_percentage'):
                    if (correct_period['start_month'] != answer_period['start_month'] or
                        correct_period['end_month'] != answer_period['end_month']):
                        error = (f"时间周期错误: 答案为T+{answer_period['start_month']}至T+{answer_period['end_month']}，"
                               f"应为T+{correct_period['start_month']}至T+{correct_period['end_month']}")
                        return False, error

                    # 检查发放比例
                    if correct_period['percentage'] != answer_period['percentage']:
                        error = (f"发放比例错误: 答案为各发放{answer_period['percentage']}%，"
                               f"应为各发放{correct_period['percentage']}%")
                        return False, error

                # 检查连续月数
                if (correct_period.get('type') == 'consecutive_months' and
                    answer_period.get('type') == 'consecutive_months'):
                    if correct_period['months'] != answer_period['months']:
                        error = (f"连续月数错误: 答案为{answer_period['months']}个月，"
                               f"应为{correct_period['months']}个月")
                        return False, error

        return True, ""

    def _extract_periods_from_text(self, text: str) -> List[Dict[str, Any]]:
        """从文本中提取时间周期（Phase 2 新增）"""
        periods = []

        # 模式1: T+n 至 T+m 各发放X%
        pattern1 = r'T\+(\d+)\s*至\s*T\+(\d+).*?各\s*发放\s*(\d+)%'
        matches1 = re.finditer(pattern1, text)
        for match in matches1:
            periods.append({
                'type': 't_range_percentage',
                'start_month': int(match.group(1)),
                'end_month': int(match.group(2)),
                'percentage': int(match.group(3)),
                'duration': int(match.group(2)) - int(match.group(1)) + 1,
                'description': match.group(0)
            })

        # 模式2: T+n 至 T+m
        pattern2 = r'T\+(\d+)\s*至\s*T\+(\d+)月?'
        matches2 = re.finditer(pattern2, text)
        for match in matches2:
            periods.append({
                'type': 't_range_percentage',
                'start_month': int(match.group(1)),
                'end_month': int(match.group(2)),
                'percentage': None,
                'duration': int(match.group(2)) - int(match.group(1)) + 1,
                'description': match.group(0)
            })

        return periods

    # ======================================


# 全局实例
_table_parser = None


def get_table_parser(config: Dict[str, Any] = None) -> UniversalTableParser:
    """获取表格解析器实例"""
    global _table_parser
    if _table_parser is None:
        _table_parser = UniversalTableParser(config or {})
    return _table_parser


# 辅助函数：从文档块中检测和提取表格
def extract_tables_from_documents(
    documents: List[Dict],
    table_parser: UniversalTableParser = None
) -> List[ParsedTable]:
    """
    从文档中提取表格

    Args:
        documents: 文档列表
        table_parser: 表格解析器实例

    Returns:
        解析后的表格列表
    """
    if table_parser is None:
        table_parser = get_table_parser()

    tables = []

    logger.info(f"🔍 [Phase 2] 表格解析器开始处理 {len(documents)} 个文档")

    for doc in documents:
        text = doc.get("text", "")
        source = doc.get("source_document",
                       doc.get("metadata", {}).get("filename",
                       doc.get("filename", "unknown")))

        # 检测表格标记
        table_start = text.find("## 表格")
        if table_start == -1:
            table_start = text.find("## 表格对比数据")

        if table_start != -1:
            # 提取表格内容（简化处理：从标记开始到下一个##之前）
            table_end = text.find("## ", table_start + 10)
            if table_end == -1:
                table_end = len(text)

            table_text = text[table_start:table_end].strip()
            if table_text:
                parsed_table = table_parser.parse_from_text(table_text, source)
                tables.append(parsed_table)
                logger.info(f"✅ [Phase 2] 从 {source} 解析到 {parsed_table.table_type.value} 类型表格，{len(parsed_table.rows)} 行数据")

    logger.info(f"📊 [Phase 2] 共从 {len(documents)} 个文档中提取到 {len(tables)} 个表格")

    # Phase 2: 提取并记录时间周期信息
    if tables:
        time_periods = table_parser.extract_time_periods(tables)
        if time_periods:
            logger.info(f"⏰ [Phase 2] 从表格中提取到 {len(time_periods)} 个时间周期规则")

    return tables


if __name__ == "__main__":
    # 测试代码
    test_table = """
## 表格对比数据
套餐名称 | 月租 | 流量 | 套外语音
29元潮玩青春卡 | 29元 | 30GB | 0.19元/分钟
59元潮玩青春卡 | 59元 | 50GB | 0.19元/分钟
"""

    parser = UniversalTableParser()
    table = parser.parse_from_text(test_table, "test.txt")

    print(f"表格类型: {table.table_type.value}")
    print(f"列数: {len(table.columns)}")
    print(f"行数: {len(table.rows)}")
    print("\nMarkdown格式:")
    print(table.to_markdown())

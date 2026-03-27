# optimized_table_analyzer.py
"""
优化的表格分析器 - 提高表格查询准确率
主要改进：
1. 更精确的转置表格检测
2. 增强的列名解析
3. 智能数值提取
4. 查询意图理解
5. 与LLM的更好集成
"""

import pandas as pd
import re
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OptimizedQueryResult:
    """优化的查询结果"""
    answer: str
    data: Optional[pd.DataFrame]
    confidence: float
    source_table: int
    explanation: str
    query_type: str  # comparison, calculation, lookup, general
    matched_rows: int
    extraction_method: str


class OptimizedTableAnalyzer:
    """优化的表格分析器"""

    # 转置表格特征（更精确的检测）
    TRANSPOSED_FEATURES = {
        "column_keywords": [
            "区域服务商", "委托厅", "全业务", "非区域", "自营",
            "Shopping", "校园", "微格", "社会渠道", "厅",
            "129元", "59元", "69元", "79元", "99元", "39元",
            "6星C", "6星B", "5星", "4星", "3星",
            "属地", "非属地", "对比", "服补"
        ],
        "row_keywords": [
            "倍数", "比例", "时间", "发放", "档位", "门槛",
            "金额", "星级", "费用", "分成", "激励", "补贴",
            "系数", "额度", "天数", "月数"
        ]
    }

    # 数值模式
    NUMERIC_PATTERNS = {
        "money": r'\d+(?:\.\d+)?元',
        "percentage": r'\d+(?:\.\d+)?%',
        "ratio": r'\d+(?:\.\d+)?倍',
        "time_range": r'T\d+(?:\s*[-~到]\s*T\d+)?',
        "months": r'\d+(?:\.\d+)?个月?',
        "days": r'\d+(?:\.\d+)?天',
        "pure_number": r'\d+(?:\.\d+)?'
    }

    def __init__(self, base_analyzer=None):
        """
        初始化优化表格分析器

        Args:
            base_analyzer: 基础表格分析器（用于向后兼容）
        """
        self.base_analyzer = base_analyzer
        self.tables = []
        self._query_cache = {}

        # 如果提供了基础分析器，复制其表格数据
        if base_analyzer and hasattr(base_analyzer, 'tables'):
            self.tables = base_analyzer.tables
            logger.info(f"从基础分析器加载了 {len(self.tables)} 个表格")

        logger.info("✅ 优化表格分析器初始化完成")

    def load_from_base_analyzer(self, base_analyzer):
        """从基础分析器加载表格"""
        self.base_analyzer = base_analyzer
        self.tables = base_analyzer.tables
        logger.info(f"加载了 {len(self.tables)} 个表格")

    def query(self, natural_query: str, top_k: int = 3) -> List[OptimizedQueryResult]:
        """
        优化的自然语言查询

        Args:
            natural_query: 自然语言查询
            top_k: 返回结果数量

        Returns:
            优化查询结果列表
        """
        # 检查缓存
        cache_key = f"{natural_query}:{top_k}"
        if cache_key in self._query_cache:
            return self._query_cache[cache_key]

        results = []

        # 1. 分析查询意图
        query_intent = self._analyze_query_intent(natural_query)
        logger.info(f"查询意图: {query_intent}")

        # 2. 查找相关表格（改进的相关性评分）
        relevant_tables = self._find_relevant_tables_optimized(natural_query)
        logger.info(f"找到 {len(relevant_tables)} 个相关表格")

        # 3. 对每个表格执行查询
        for table_info in relevant_tables[:top_k]:
            df = self._get_dataframe(table_info.index)
            if df is None:
                continue

            # 根据查询意图选择查询方法
            result = self._execute_optimized_query(
                df, natural_query, table_info, query_intent
            )
            if result:
                results.append(result)

        # 缓存结果
        self._query_cache[cache_key] = results
        return results

    def _analyze_query_intent(self, query: str) -> str:
        """分析查询意图"""
        # 对比类查询
        if any(kw in query for kw in ["对比", "差异", "区别", "不同", "比较", "分别"]):
            return "comparison"

        # 计算类查询
        if any(kw in query for kw in ["计算", "多少", "费用", "分成", "合计", "总计"]):
            return "calculation"

        # 查找类查询
        if any(kw in query for kw in ["哪些", "什么", "如何", "怎么"]):
            return "lookup"

        # 条件查询
        if any(kw in query for kw in ["满足", "条件", "要求", "如果"]):
            return "conditional"

        return "general"

    def _find_relevant_tables_optimized(self, query: str) -> List[Any]:
        """优化的相关表格查找"""
        table_scores = []

        # 提取查询关键词（增强版）
        keywords = self._extract_query_keywords(query)
        logger.debug(f"查询关键词: {keywords[:15]}")

        for table in self.tables:
            score = 0
            reasons = []

            # 1. 表头匹配（高权重）
            header_text = " ".join(table.headers).lower()
            for kw in keywords:
                if kw.lower() in header_text:
                    score += 5
                    reasons.append(f"表头匹配: {kw}")

            # 2. 表格类型匹配
            if table.table_type == "fee_schedule":
                if any(kw in query for kw in ["费用", "分成", "激励", "手续费", "酬金"]):
                    score += 8
                    reasons.append("费用标准表类型匹配")
            elif table.table_type == "product_list":
                if any(kw in query for kw in ["产品", "套餐", "优惠", "ID"]):
                    score += 8
                    reasons.append("产品列表表类型匹配")

            # 3. 表格内容匹配（采样前20行）
            table_content = ""
            for row in table.data[:20]:
                table_content += " " + " ".join(row)

            table_content_lower = table_content.lower()
            for kw in keywords:
                if kw.lower() in table_content_lower:
                    score += 2

            # 4. 特殊模式匹配
            # 检查是否包含对比相关的关键词
            if any(kw in query for kw in ["区域服务商", "委托厅", "属地考核"]):
                # 检查表格是否为对比表结构
                is_transposed = self._is_transposed_table(table)
                if is_transposed:
                    score += 6
                    reasons.append("转置对比表结构匹配")

            if score > 0:
                table_scores.append((table, score, reasons))

        # 按分数排序
        table_scores.sort(key=lambda x: x[1], reverse=True)
        logger.debug(f"表格评分: {[(t.table_type, s) for t, s, _ in table_scores[:3]]}")

        return [t for t, _, _ in table_scores[:5]]

    def _extract_query_keywords(self, query: str) -> List[str]:
        """提取查询关键词（增强版）"""
        keywords = []

        # 1. 长中文短语（4-10字）
        long_phrases = re.findall(r'[\u4e00-\u9fa5]{4,10}', query)
        keywords.extend(long_phrases)

        # 2. 数字+中文组合（高精度）
        patterns = re.findall(
            r'\d+[元GB级星级月笔C%天]+[A-Z]?|'
            r'T\d+(?:\s*[-~到]\s*T\d+)?|'
            r'\d+\+\s*[元天]?',
            query
        )
        keywords.extend(patterns)

        # 3. 中短中文短语（2-3字）
        short_phrases = re.findall(r'[\u4e00-\u9fa5]{2,3}', query)
        keywords.extend(short_phrases)

        # 4. 特殊业务术语
        business_terms = [
            '属地考核', '首充手续费', '套餐分成', '达量激励',
            '万能副卡', '潮玩青春卡', '全家享', '区域服务商',
            '委托厅', '全业务', '服务运营激励', '阶段激励',
            '新入网', '实名手续费', '流量赠送', '功能费减免'
        ]
        for term in business_terms:
            if term in query:
                keywords.append(term)

        # 去重
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)

        return unique_keywords[:30]

    def _is_transposed_table(self, table: Any) -> bool:
        """检测是否为转置表格"""
        # 检查列名
        column_text = " ".join([str(col) for col in table.headers])

        feature_count = 0
        for kw in self.TRANSPOSED_FEATURES["column_keywords"]:
            if kw in column_text:
                feature_count += 1

        # 检查第一列是否为指标
        if table.data:
            first_col_values = " ".join([str(row[0]) for row in table.data[:10]])
            for kw in self.TRANSPOSED_FEATURES["row_keywords"]:
                if kw in first_col_values:
                    feature_count += 1
                    break

        return feature_count >= 2

    def _execute_optimized_query(
        self,
        df: pd.DataFrame,
        query: str,
        table_info: Any,
        query_intent: str
    ) -> Optional[OptimizedQueryResult]:
        """执行优化的查询"""
        try:
            # 检测表格类型
            is_transposed = self._is_transposed_table_df(df)

            if query_intent == "comparison" and is_transposed:
                return self._query_comparison_transposed(df, query, table_info)
            elif query_intent == "calculation":
                return self._query_calculation(df, query, table_info)
            elif query_intent == "lookup":
                return self._query_lookup(df, query, table_info)
            else:
                return self._query_general(df, query, table_info)

        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            return None

    def _is_transposed_table_df(self, df: pd.DataFrame) -> bool:
        """检测DataFrame是否为转置表格"""
        if len(df.columns) < 3:
            return False

        column_text = " ".join([str(col) for col in df.columns])

        feature_count = 0
        for kw in self.TRANSPOSED_FEATURES["column_keywords"]:
            if kw in column_text:
                feature_count += 1

        if len(df) > 0:
            first_col_values = " ".join([str(val) for val in df.iloc[:10, 0]])
            for kw in self.TRANSPOSED_FEATURES["row_keywords"]:
                if kw in first_col_values:
                    feature_count += 1
                    break

        return feature_count >= 2

    def _query_comparison_transposed(
        self,
        df: pd.DataFrame,
        query: str,
        table_info: Any
    ) -> Optional[OptimizedQueryResult]:
        """查询转置对比表"""
        try:
            # 解析查询目标列
            target_columns = self._parse_target_columns(df, query)

            # 解析查询目标行
            target_rows = self._parse_target_rows(df, query)

            # 构建结果
            result_parts = []
            result_parts.append("## 对比数据")
            result_parts.append("")

            # 添加列说明
            result_parts.append("【对比类别】")
            for i, col in enumerate(target_columns[:5], 1):
                result_parts.append(f"{i}. {col}")
            result_parts.append("")

            # 添加数据对比
            result_parts.append("【数据详情】")
            matched_count = 0

            first_col = df.columns[0]
            for row_label in target_rows[:15]:
                matching_rows = df[df[first_col] == row_label]
                if len(matching_rows) == 0:
                    continue

                row = matching_rows.iloc[0]
                values = [f"指标: {row_label}"]

                for col in target_columns:
                    val = str(row.get(col, ""))
                    if val and val not in ["nan", "", "--"]:
                        values.append(f"{col}={val}")

                if len(values) > 1:
                    result_parts.append(" | ".join(values))
                    matched_count += 1

            answer = "\n".join(result_parts)

            return OptimizedQueryResult(
                answer=answer,
                data=df,
                confidence=0.85,
                source_table=table_info.index,
                explanation=f"从转置对比表中提取了 {matched_count} 个指标的对比数据",
                query_type="comparison",
                matched_rows=matched_count,
                extraction_method="transposed_table"
            )

        except Exception as e:
            logger.error(f"转置表格查询失败: {e}")
            return None

    def _parse_target_columns(self, df: pd.DataFrame, query: str) -> List[str]:
        """解析目标列"""
        target_columns = []

        # 根据查询确定目标列
        if "区域服务商" in query or ("属地" in query and "非属地" not in query):
            for col in df.columns:
                col_str = str(col)
                if "区域" in col_str and "非区域" not in col_str:
                    target_columns.append(col)

        if "非区域" in query or "委托厅" in query or "全业务" in query:
            for col in df.columns:
                col_str = str(col)
                if any(kw in col_str for kw in ["委托", "全业务", "自营", "非区域", "Shopping"]):
                    if col not in target_columns:
                        target_columns.append(col)

        # 如果没有明确指定，使用所有数据列
        if not target_columns:
            for col in df.columns[1:]:  # 跳过第一列
                col_str = str(col)
                if col_str and col_str != "nan":
                    target_columns.append(col)

        return target_columns[:6]  # 最多6列

    def _parse_target_rows(self, df: pd.DataFrame, query: str) -> List[str]:
        """解析目标行"""
        # 提取查询中的关键词
        keywords = self._extract_query_keywords(query)

        target_rows = []
        first_col = df.columns[0]

        # 计算每行的相关性分数
        row_scores = []
        for idx, row in df.iterrows():
            row_label = str(row[first_col])
            if row_label == "nan":
                continue

            score = 0
            for kw in keywords:
                if kw.lower() in row_label.lower():
                    score += len(kw)  # 长关键词权重更高

            if score > 0:
                row_scores.append((row_label, score))

        # 排序并返回
        row_scores.sort(key=lambda x: x[1], reverse=True)
        return [label for label, _ in row_scores[:20]]

    def _query_calculation(
        self,
        df: pd.DataFrame,
        query: str,
        table_info: Any
    ) -> Optional[OptimizedQueryResult]:
        """计算类查询"""
        # 提取数值
        numeric_data = self._extract_numeric_data(df, query)

        if not numeric_data:
            return None

        # 构建结果
        result_parts = ["## 计算相关数据", ""]
        result_parts.extend(numeric_data[:20])

        return OptimizedQueryResult(
            answer="\n".join(result_parts),
            data=df,
            confidence=0.75,
            source_table=table_info.index,
            explanation=f"提取了 {len(numeric_data)} 条数值数据用于计算",
            query_type="calculation",
            matched_rows=len(numeric_data),
            extraction_method="numeric_extraction"
        )

    def _extract_numeric_data(self, df: pd.DataFrame, query: str) -> List[str]:
        """提取数值数据"""
        results = []
        keywords = self._extract_query_keywords(query)

        for idx, row in df.iterrows():
            row_text = " ".join([str(val) for val in row.values])

            # 检查是否包含关键词
            if not any(kw.lower() in row_text.lower() for kw in keywords):
                continue

            # 提取数值
            for pattern_name, pattern in self.NUMERIC_PATTERNS.items():
                matches = re.findall(pattern, row_text)
                if matches:
                    results.append(f"行{idx+1}: {row_text[:100]}")
                    break

        return results

    def _query_lookup(
        self,
        df: pd.DataFrame,
        query: str,
        table_info: Any
    ) -> Optional[OptimizedQueryResult]:
        """查找类查询"""
        keywords = self._extract_query_keywords(query)

        scored_rows = []
        for idx, row in df.iterrows():
            row_text = " ".join([str(val) for val in row.values])
            score = sum(1 for kw in keywords if kw.lower() in row_text.lower())

            if score > 0:
                scored_rows.append((idx, row_text, score))

        scored_rows.sort(key=lambda x: x[2], reverse=True)

        if scored_rows:
            result_parts = ["## 查找结果", ""]
            for idx, row_text, score in scored_rows[:5]:
                result_parts.append(f"结果{len(result_parts)}: {row_text[:150]}")

            return OptimizedQueryResult(
                answer="\n".join(result_parts),
                data=df,
                confidence=0.7,
                source_table=table_info.index,
                explanation=f"找到 {len(scored_rows)} 个匹配结果",
                query_type="lookup",
                matched_rows=len(scored_rows),
                extraction_method="keyword_match"
            )

        return None

    def _query_general(
        self,
        df: pd.DataFrame,
        query: str,
        table_info: Any
    ) -> Optional[OptimizedQueryResult]:
        """通用查询"""
        return self._query_lookup(df, query, table_info)

    def _get_dataframe(self, table_index: int) -> Optional[pd.DataFrame]:
        """获取表格的DataFrame"""
        if table_index >= len(self.tables):
            return None

        table = self.tables[table_index]
        df = pd.DataFrame(table.data, columns=table.headers)
        return df

    def format_for_llm(self, query: str, results: List[OptimizedQueryResult]) -> str:
        """为LLM格式化查询结果"""
        if not results:
            return "未找到相关表格数据"

        lines = []
        lines.append("## 表格查询结果")
        lines.append("")
        lines.append(f"查询: {query}")
        lines.append(f"找到 {len(results)} 个相关表格")
        lines.append("")

        for i, result in enumerate(results, 1):
            lines.append(f"### 结果 {i}")
            lines.append(f"查询类型: {result.query_type}")
            lines.append(f"置信度: {result.confidence:.2f}")
            lines.append(f"说明: {result.explanation}")
            lines.append("")
            lines.append("数据:")
            lines.append(result.answer[:1000])  # 限制长度
            lines.append("")

        return "\n".join(lines)

    def clear_cache(self):
        """清除查询缓存"""
        self._query_cache.clear()
        logger.info("查询缓存已清除")


# 全局单例
_optimized_analyzer = None


def get_optimized_table_analyzer(base_analyzer=None) -> OptimizedTableAnalyzer:
    """获取优化表格分析器实例"""
    global _optimized_analyzer
    if _optimized_analyzer is None:
        _optimized_analyzer = OptimizedTableAnalyzer(base_analyzer)
    elif base_analyzer:
        _optimized_analyzer.load_from_base_analyzer(base_analyzer)
    return _optimized_analyzer

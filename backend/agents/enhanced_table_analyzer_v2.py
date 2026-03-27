"""
增强版表格分析器 - 提升表格理解能力
核心改进：
1. 语义索引 - 使用向量相似度查找相关表格
2. 结构化重建 - 将表格转换为LLM友好格式
3. 智能查询理解 - 更准确的表格数据提取
4. 精确数值提取 - 使用PrecisionTableExtractor确保数值准确性
"""

import pandas as pd
import re
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 导入精确表格提取器
try:
    from agents.precision_table_extractor import (
        PrecisionTableExtractor,
        get_precision_extractor,
        TableExtractionResult,
        ExtractedValue
    )
    PRECISION_EXTRACTOR_AVAILABLE = True
except ImportError:
    PRECISION_EXTRACTOR_AVAILABLE = False
    logger.warning("⚠️ 精确表格提取器不可用")


@dataclass
class TableQueryResult:
    """表格查询结果"""
    answer: str
    confidence: float
    source_table: int
    table_type: str
    structured_data: Optional[Dict[str, Any]] = None
    explanation: str = ""


class EnhancedTableAnalyzer:
    """增强版表格分析器"""

    def __init__(self, base_analyzer, embedding_service=None):
        """
        初始化增强版表格分析器

        Args:
            base_analyzer: 基础ChannelTableAnalyzer实例
            embedding_service: 嵌入服务（用于语义索引）
        """
        self.base = base_analyzer
        self.embedding_service = embedding_service

        # 语义索引缓存
        self._semantic_index = {}
        self._build_semantic_index()

        # 初始化精确表格提取器
        self.precision_extractor = None
        if PRECISION_EXTRACTOR_AVAILABLE:
            try:
                self.precision_extractor = get_precision_extractor()
                logger.info("✅ 精确表格提取器已启用")
            except Exception as e:
                logger.warning(f"⚠️ 精确表格提取器初始化失败: {e}")

        logger.info("✅ 增强版表格分析器初始化完成")

    def _build_semantic_index(self):
        """为所有表格建立语义索引"""
        if not self.embedding_service:
            logger.warning("⚠️ 未提供嵌入服务，跳过语义索引")
            return

        for table in self.base.tables:
            # 生成表格描述
            description = self._create_table_description(table)

            # 生成嵌入向量
            try:
                self._semantic_index[table.index] = {
                    "description": description,
                    "embedding": self.embedding_service.encode(description),
                    "headers": table.headers,
                    "type": table.table_type
                }
            except Exception as e:
                logger.warning(f"⚠️ 表格 {table.index} 语义索引失败: {e}")

        logger.info(f"📊 已为 {len(self._semantic_index)} 个表格建立语义索引")

    def _create_table_description(self, table) -> str:
        """创建表格的语义描述"""
        parts = []

        # 添加表头
        if table.headers:
            parts.append("表格列名: " + ", ".join(table.headers[:10]))

        # 添加前几行数据样本
        sample_rows = []
        for row in table.data[:3]:
            row_text = " ".join([str(cell) for cell in row if cell])
            if row_text:
                sample_rows.append(row_text)

        if sample_rows:
            parts.append("数据示例: " + "; ".join(sample_rows))

        # 添加表格类型
        parts.append(f"表格类型: {table.table_type}")

        return " | ".join(parts)

    def query(self, natural_query: str, top_k: int = 3) -> List[TableQueryResult]:
        """
        增强的表格查询

        Args:
            natural_query: 自然语言查询
            top_k: 返回结果数量

        Returns:
            查询结果列表
        """
        results = []

        # 1. 语义查找相关表格
        relevant_tables = self._find_relevant_tables_semantic(natural_query, top_k)

        logger.info(f"📊 语义查找找到 {len(relevant_tables)} 个相关表格")

        # 2. 对每个相关表格执行深度查询
        for table_info in relevant_tables:
            result = self._deep_query(table_info, natural_query)
            if result and result.confidence > 0.3:
                results.append(result)

        # 3. 按置信度排序
        results.sort(key=lambda x: x.confidence, reverse=True)

        return results[:top_k]

    def _find_relevant_tables_semantic(self, query: str, top_k: int = 5) -> List[Dict]:
        """使用语义相似度查找相关表格"""
        if not self._semantic_index or not self.embedding_service:
            # 降级到基础方法
            return self.base._find_relevant_tables(query)

        # 生成查询嵌入
        try:
            query_emb = self.embedding_service.encode(query)
        except Exception as e:
            logger.warning(f"查询编码失败: {e}")
            return self.base._find_relevant_tables(query)

        # 计算相似度
        similarities = []
        for table_idx, table_data in self._semantic_index.items():
            # 计算余弦相似度
            sim = self._cosine_similarity(query_emb, table_data["embedding"])
            similarities.append({
                "index": table_idx,
                "similarity": sim,
                "type": table_data["type"],
                "headers": table_data["headers"]
            })

        # 排序并返回top_k
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return [s for s in similarities if s["similarity"] > 0.2][:top_k]

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        try:
            return float(np.dot(vec1, vec2) /
                        (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
        except:
            return 0.0

    def _deep_query(self, table_info: Dict, query: str) -> Optional[TableQueryResult]:
        """深度查询表格"""
        table_idx = table_info["index"]
        df = self.base.to_dataframe(table_idx)

        if df is None:
            return None

        # 检测表格类型并选择查询策略
        table_type = table_info.get("type", "general")

        if table_type == "fee_schedule" or table_type == "comparison":
            return self._query_comparison_table(df, query, table_idx, table_type)
        elif table_type == "product_list":
            return self._query_product_table(df, query, table_idx)
        else:
            return self._query_general_table(df, query, table_idx)

    def _query_comparison_table(
        self, df: pd.DataFrame, query: str, table_idx: int, table_type: str
    ) -> Optional[TableQueryResult]:
        """查询对比表格"""
        # 检测是否为转置表格
        is_transposed = self._is_transposed_table(df, query)

        if is_transposed:
            return self._query_transposed_table(df, query, table_idx, table_type)
        else:
            return self._query_standard_comparison(df, query, table_idx, table_type)

    def _is_transposed_table(self, df: pd.DataFrame, query: str) -> bool:
        """检测是否为转置表格"""
        # 检查列名
        column_text = " ".join([str(col) for col in df.columns])

        # 转置表格特征
        transposed_indicators = [
            "区域服务商", "非区域", "委托厅", "全业务",
            "渠道", "校园", "自营",
            "对比", "差异"
        ]

        count = sum(1 for ind in transposed_indicators if ind in column_text)
        return count >= 2

    def _query_transposed_table(
        self, df: pd.DataFrame, query: str, table_idx: int, table_type: str
    ) -> Optional[TableQueryResult]:
        """查询转置表格"""
        # 提取用户关心的列
        target_columns = self._extract_target_columns(df, query)

        # 构建结构化答案
        answer_parts = []
        structured_data = {}

        first_col = df.columns[0] if len(df.columns) > 0 else None

        # 获取行标签（指标名称）
        row_labels = []
        if first_col:
            for idx, row in df.iterrows():
                label = str(row[first_col])
                if label and label.strip() and label not in row_labels:
                    row_labels.append(label)

        # 提取每个指标的数值
        for label in row_labels[:15]:
            matching_rows = df[df[first_col] == label]
            if len(matching_rows) > 0:
                row = matching_rows.iloc[0]
                values = {}
                for col in target_columns:
                    val = str(row.get(col, ""))
                    if val and val not in ["nan", "", "--"]:
                        col_name = self._simplify_column_name(col)
                        values[col_name] = val

                if values:
                    structured_data[label] = values
                    # 构建可读文本
                    value_str = ", ".join([f"{k}={v}" for k, v in values.items()])
                    answer_parts.append(f"- {label}: {value_str}")

        if answer_parts:
            answer = "【对比数据】\n" + "\n".join(answer_parts)

            return TableQueryResult(
                answer=answer,
                confidence=0.85,
                source_table=table_idx,
                table_type=table_type,
                structured_data=structured_data,
                explanation=f"从转置表格中找到 {len(structured_data)} 个对比项"
            )

        return None

    def _extract_target_columns(self, df: pd.DataFrame, query: str) -> List[str]:
        """根据查询提取目标列"""
        columns = [str(col) for col in df.columns]
        target_cols = []

        # 根据查询关键词确定目标列
        if any(kw in query for kw in ["区域服务商", "服务商"]):
            for col in columns:
                if "区域" in col and "非区域" not in col:
                    target_cols.append(col)

        if any(kw in query for kw in ["非区域", "委托厅", "全业务"]):
            for col in columns:
                if any(kw in col for kw in ["委托", "全业务", "自营", "非区域"]):
                    if col not in target_cols:
                        target_cols.append(col)

        # 如果没有明确指定，使用所有数据列
        if not target_cols:
            target_cols = [col for col in columns[1:] if col and col.strip()]

        return target_cols

    def _simplify_column_name(self, col_name: str) -> str:
        """简化列名"""
        # 提取关键部分
        if "区域服务商" in col_name:
            return "区域服务商"
        elif "委托厅" in col_name or "全业务" in col_name:
            return "非区域/委托厅"
        else:
            return col_name[:20]

    def _query_standard_comparison(
        self, df: pd.DataFrame, query: str, table_idx: int, table_type: str
    ) -> Optional[TableQueryResult]:
        """查询标准对比表格"""
        # 提取查询元素
        query_elements = self.base._extract_query_elements(query)

        # 对每行计算相关性
        scored_rows = []
        for idx, row in df.iterrows():
            row_text = " ".join([str(v) for v in row.values])
            score = self.base._calculate_relevance(row_text, query_elements, query)
            if score > 0:
                scored_rows.append((idx, row, score))

        if scored_rows:
            scored_rows.sort(key=lambda x: x[2], reverse=True)
            top_row = scored_rows[0]

            # 构建答案
            answer_parts = []
            for col in df.columns:
                val = str(top_row[1][col])
                if val and val != "nan":
                    answer_parts.append(f"{col}: {val}")

            answer = "【相关数据】\n" + "\n".join(answer_parts)

            return TableQueryResult(
                answer=answer,
                confidence=min(top_row[2], 1.0),
                source_table=table_idx,
                table_type=table_type,
                explanation=f"找到匹配度 {top_row[2]:.2f} 的数据"
            )

        return None

    def _query_product_table(
        self, df: pd.DataFrame, query: str, table_idx: int
    ) -> Optional[TableQueryResult]:
        """查询产品表格"""
        # 提取产品关键词
        keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', query)

        matches = []
        for idx, row in df.iterrows():
            row_text = " ".join([str(v) for v in row.values])
            match_count = sum(1 for kw in keywords if kw in row_text)

            if match_count >= 2:
                matches.append((idx, row_text, match_count))

        if matches:
            matches.sort(key=lambda x: x[2], reverse=True)
            answer = "【产品信息】\n" + "\n".join([m[1][:100] for m in matches[:3]])

            return TableQueryResult(
                answer=answer,
                confidence=0.8,
                source_table=table_idx,
                table_type="product_list",
                explanation=f"找到 {len(matches)} 个匹配产品"
            )

        return None

    def _query_general_table(
        self, df: pd.DataFrame, query: str, table_idx: int
    ) -> Optional[TableQueryResult]:
        """通用表格查询"""
        query_elements = self.base._extract_query_elements(query)

        scored_rows = []
        for idx, row in df.iterrows():
            row_text = " ".join([str(v) for v in row.values])
            score = self.base._calculate_relevance(row_text, query_elements, query)
            if score > 0.2:
                scored_rows.append((idx, row_text, score))

        if scored_rows:
            scored_rows.sort(key=lambda x: x[2], reverse=True)
            top_rows = scored_rows[:3]

            answer_parts = []
            for idx, row_text, score in top_rows:
                answer_parts.append(f"匹配度 {score:.2f}: {row_text[:150]}")

            answer = "【查询结果】\n" + "\n\n".join(answer_parts)

            return TableQueryResult(
                answer=answer,
                confidence=top_rows[0][2],
                source_table=table_idx,
                table_type="general",
                explanation=f"找到 {len(scored_rows)} 个相关结果"
            )

        return None

    def format_for_llm(self, table_idx: int, query: str) -> str:
        """
        为LLM格式化表格数据

        这是关键方法 - 将表格转换为LLM能理解的格式
        优先使用精确提取器进行格式化
        """
        df = self.base.to_dataframe(table_idx)

        if df is None:
            return f"表格 {table_idx} 数据不可用"

        # 优先使用精确提取器
        if self.precision_extractor:
            try:
                return self._format_with_precision_extractor(table_idx, df, query)
            except Exception as e:
                logger.warning(f"⚠️ 精确提取器格式化失败，降级到标准方法: {e}")

        # 降级到标准方法
        return self._format_standard(table_idx, df, query)

    def _format_with_precision_extractor(self, table_idx: int, df: pd.DataFrame, query: str) -> str:
        """使用精确提取器格式化表格"""
        # 分析表格结构
        table_result = self.precision_extractor.analyze_table_structure(df)

        # 使用精确提取器的格式化方法
        formatted = self.precision_extractor.format_for_llm(table_result, query)

        # 添加表格索引信息
        header = f"## 表格 {table_idx} (精确提取)\n"
        header += f"表格类型: {'转置对比表' if table_result.is_transposed else '标准数据表'}\n"
        header += f"数据规模: {len(table_result.row_labels)} 行 × {len(table_result.column_labels)} 列\n\n"

        return header + formatted

    def _format_standard(self, table_idx: int, df: pd.DataFrame, query: str) -> str:
        """标准格式化方法（降级用）"""
        table = self.base.tables[table_idx]

        # 构建结构化输出
        output = []
        output.append(f"## 表格 {table_idx} ({table.table_type}类型)")
        output.append(f"")
        output.append(f"【表格结构】")
        output.append(f"- 列名: {', '.join(table.headers[:8])}")
        output.append(f"- 行数: {table.rows}")
        output.append("")

        # 根据查询选择相关行
        relevant_rows = self._get_relevant_rows_for_query(df, query)

        output.append(f"【相关数据】")
        for idx, row in relevant_rows.iterrows():
            row_parts = []
            for col in df.columns:
                val = str(row[col])
                if val and val != "nan":
                    # 格式化：列名 = 值
                    row_parts.append(f"{col}={val}")
            output.append(f"  行{idx+1}: {' | '.join(row_parts[:6])}")

        return "\n".join(output)

    def _get_relevant_rows_for_query(
        self, df: pd.DataFrame, query: str, max_rows: int = 10
    ) -> pd.DataFrame:
        """获取与查询相关的行"""
        query_elements = self.base._extract_query_elements(query)

        if not query_elements:
            return df.head(max_rows)

        # 计算每行的相关性
        scored_rows = []
        for idx, row in df.iterrows():
            row_text = " ".join([str(v) for v in row.values])
            score = self.base._calculate_relevance(row_text, query_elements, query)
            scored_rows.append((idx, score))

        # 排序并返回top行
        scored_rows.sort(key=lambda x: x[1], reverse=True)
        top_indices = [idx for idx, _ in scored_rows[:max_rows]]

        return df.loc[top_indices]


def get_enhanced_table_analyzer(base_analyzer, embedding_service=None):
    """获取增强版表格分析器实例"""
    return EnhancedTableAnalyzer(base_analyzer, embedding_service)

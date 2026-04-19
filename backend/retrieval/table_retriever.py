"""
表格检索器 - 确保检索到完整表格
使用智能合并策略，避免硬编码
"""
from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)


class TableRetriever:
    """表格检索器 - 智能合并表格片段"""

    def __init__(self, vector_storage):
        self.vector_storage = vector_storage
        self.chunk_size = 1000

    def retrieve_complete_tables(
        self,
        query: str,
        top_k: int = 5,
        retrieval_multiplier: int = 3
    ) -> List[Dict]:
        """
        检索相关表格，确保返回完整表格

        策略：
        1. 增加检索数量（top_k * retrieval_multiplier）
        2. 识别表格边界（通过内容特征）
        3. 合并同一表格的多个片段
        4. 按相关性排序

        Args:
            query: 查询文本
            top_k: 返回的表格数量
            retrieval_multiplier: 检索倍数（默认检索3倍数量）

        Returns:
            合并后的完整表格列表
        """
        # 1. 增加检索数量
        chunks = self._retrieve_chunks(
            query,
            top_k=top_k * retrieval_multiplier
        )

        if not chunks:
            logger.warning("未检索到任何相关内容")
            return []

        # 2. 识别和合并表格片段
        tables = self._merge_table_chunks(chunks)

        if not tables:
            # 如果没有检测到表格，返回原始片段
            logger.info("未检测到表格结构，返回原始检索结果")
            return chunks[:top_k]

        # 3. 按相关性排序
        tables = self._rank_tables(tables, query)

        logger.info(f"表格检索: 原始片段{len(chunks)}个 -> 合并后{len(tables)}个表格")

        return tables[:top_k]

    def _retrieve_chunks(self, query: str, top_k: int) -> List[Dict]:
        """执行向量检索"""
        try:
            # 使用嵌入服务生成查询向量
            import sys
            embedding_service = sys.modules.get('_embedding_service_instance')

            if not embedding_service:
                logger.warning("嵌入服务不可用")
                return []

            query_vector = embedding_service.embed_text(query)

            # 执行向量搜索（方案2优化：降低阈值从0.25到0.05）
            chunks = self.vector_storage.search(
                query_vector=query_vector,
                top_k=top_k,
                score_threshold=0.05  # 降低阈值以获取更多相关内容
            )

            return chunks

        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []

    def _merge_table_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        合并属于同一表格的多个片段

        策略：
        1. 检测表格特征（不依赖硬编码的表格名称）
        2. 按来源文档和位置分组
        3. 合并同一组的片段
        """
        tables = []
        table_groups: Dict[str, List[Dict]] = {}

        for chunk in chunks:
            # 检测是否包含表格特征
            if not self._has_table_features(chunk):
                continue

            # 生成分组键（基于文档和位置）
            group_key = self._get_group_key(chunk)

            # 添加到对应分组
            if group_key not in table_groups:
                table_groups[group_key] = []

            table_groups[group_key].append(chunk)

        # 合并每个分组的片段
        for group_key, group_chunks in table_groups.items():
            merged_table = self._merge_group(group_chunks)
            tables.append(merged_table)

        return tables

    def _has_table_features(self, chunk: Dict) -> bool:
        """
        检测片段是否包含表格特征

        不使用硬编码的表格名称，而是检测结构性特征：
        - 包含多个数据项（产品名称、数字、单位等）
        - 包含表格分隔符（|、表格、行等）
        - 包含金额/流量等业务数据
        """
        text = chunk.get('text', '')

        # 表格结构性标记
        structural_indicators = [
            '|',  # Markdown表格
            '表格',
            '行1:',
            '表头:',
        ]

        # 业务数据模式（电信行业通用）
        business_patterns = [
            r'\d+GB',  # 流量
            r'\d+元',  # 金额
            r'\d+月',  # 时长
        ]

        # 检查结构性标记
        has_structure = any(indicator in text for indicator in structural_indicators)

        # 检查是否包含业务数据（多个数据点）
        import re
        data_count = 0
        for pattern in business_patterns:
            if re.search(pattern, text):
                data_count += 1

        # 如果有结构性标记或多个业务数据点，认为是表格
        return has_structure or data_count >= 2

    def _get_group_key(self, chunk: Dict) -> str:
        """
        生成分组键

        基于文档来源和内容特征，避免硬编码具体表格名
        """
        metadata = chunk.get('metadata', {})
        source = metadata.get('source_document', 'unknown')

        # 使用文档名作为主要分组依据
        # 同一文档的表格内容很可能属于同一个表格
        return f"{source}"

    def _merge_group(self, chunks: List[Dict]) -> Dict:
        """合并同一组的多个片段"""
        # 按位置排序（如果有位置信息）
        sorted_chunks = sorted(
            chunks,
            key=lambda x: x.get('metadata', {}).get('position', 0)
        )

        # 合并文本
        merged_text = self._merge_text_chunks(sorted_chunks)

        # 计算平均相关性分数
        avg_score = sum(c.get('score', 0) for c in chunks) / len(chunks)

        # 返回合并后的表格
        return {
            'id': chunks[0].get('id', f"table_{hash(merged_text)}"),  # 保留原始ID或生成新ID
            'text': merged_text,
            'score': avg_score,
            'search_type': 'table',  # 标记为表格检索结果
            'metadata': {
                'source_document': chunks[0].get('metadata', {}).get('source_document', 'unknown'),
                'chunk_count': len(chunks),
                'merged': True
            }
        }

    def _merge_text_chunks(self, chunks: List[Dict]) -> str:
        """
        合并多个文本片段

        策略：
        1. 去重重复的内容
        2. 按逻辑顺序拼接
        3. 保留结构化信息
        """
        seen_lines = set()
        merged_lines = []

        for chunk in chunks:
            text = chunk.get('text', '')
            lines = text.split('\n')

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 简单去重（完全相同的行）
                line_key = line[:50]  # 使用前50字符作为键
                if line_key not in seen_lines:
                    seen_lines.add(line_key)
                    merged_lines.append(line)

        return '\n'.join(merged_lines)

    def _rank_tables(self, tables: List[Dict], query: str) -> List[Dict]:
        """
        对表格进行相关性排序

        结合：
        1. 向量相似度分数
        2. 查询词匹配度
        3. 表格完整性（片段数量）
        """
        query_words = set(query.lower().split())

        for table in tables:
            # 基础分数：向量相似度
            base_score = table.get('score', 0)

            # 文本匹配分数
            table_text = table.get('text', '').lower()
            match_count = sum(1 for word in query_words if word in table_text)
            match_score = match_count / len(query_words) if query_words else 0

            # 完整性分数（片段越多，表格越完整）
            chunk_count = table.get('metadata', {}).get('chunk_count', 1)
            completeness_score = min(chunk_count / 5, 1.0)  # 最多5个片段为满分

            # 综合分数
            table['final_score'] = (
                base_score * 0.5 +
                match_score * 0.3 +
                completeness_score * 0.2
            )

        # 按综合分数排序
        return sorted(tables, key=lambda x: x.get('final_score', 0), reverse=True)

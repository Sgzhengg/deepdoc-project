"""
完整表格提取器 - 确保提取完整的表格内容，避免信息遗漏
使用模式匹配，避免硬编码
"""
import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class TableExtractor:
    """完整表格提取器"""

    def __init__(self):
        # 表格边界模式（不硬编码具体内容）
        self.table_start_patterns = [
            r'\|[-|\s]+\|',  # Markdown表格
            r'\+[-]+\+',  # 表格分隔线
            r'行\d+[:|]',  # 编号行
            r'表头[:|]',  # 表头行
        ]

    def extract_complete_table(self, chunks: List[Dict]) -> str:
        """
        从多个片段中提取完整表格

        Args:
            chunks: 文档片段列表

        Returns:
            完整的表格文本
        """
        if not chunks:
            return ""

        # 保守策略：如果只有一个片段且内容已经完整，直接返回
        if len(chunks) == 1:
            text = chunks[0].get('text', '')
            # 检查是否是已合并的完整内容（有合理长度和结构）
            if len(text) > 200 and self._has_complete_structure(text):
                logger.info("检测到已合并的完整内容，跳过表格边界提取")
                return text

        # 1. 识别表格边界
        table_start, table_end = self._find_table_boundary(chunks)

        if table_start is None:
            logger.info("未检测到表格结构，返回原始内容")
            return self._merge_all_chunks(chunks)

        # 2. 提取完整表格
        full_table = self._extract_table_between(chunks, table_start, table_end)

        # 3. 验证提取结果 - 如果提取后内容明显变短，说明边界检测有误，返回原内容
        original_length = sum(len(c.get('text', '')) for c in chunks)
        if len(full_table) < original_length * 0.5:
            logger.warning(f"表格提取后内容过短（{len(full_table)} < {original_length * 0.5}），返回原始内容")
            return self._merge_all_chunks(chunks)

        # 4. 验证表格完整性
        if self._is_incomplete_table(full_table):
            logger.info("检测到表格不完整，尝试补全")
            full_table = self._complete_table(full_table, chunks)

        return full_table

    def _has_complete_structure(self, text: str) -> bool:
        """
        检查文本是否具有完整的结构

        指标：
        - 有合理的段落分隔
        - 有句子结束符
        - 不是单一表格行
        """
        if not text:
            return False

        lines = text.split('\n')

        # 检查是否有多个段落或句子
        sentence_endings = text.count('。') + text.count('！') + text.count('？')
        has_multiple_lines = len(lines) > 3

        # 检查是否有过多的表格分隔符（可能是表格内容）
        table_separator_count = sum(1 for line in lines if '|' in line)

        # 如果有多个行、句子结束符，且不全是表格行，认为是完整内容
        return (has_multiple_lines or sentence_endings >= 2) and table_separator_count < len(lines) * 0.8

    def _find_table_boundary(self, chunks: List[Dict]) -> Tuple[int, int]:
        """
        识别表格的起始和结束位置

        通过检测表格特征来确定边界：
        - 表格分隔符（|---|, +---+）
        - 表头行
        - 连续的表格行
        """
        all_text = []
        chunk_indices = []

        for i, chunk in enumerate(chunks):
            text = chunk.get('text', '')
            all_text.append(text)
            chunk_indices.append(i)

        merged = '\n'.join(all_text)

        # 查找表格开始（第一个表格特征）
        table_start = None
        for start_pattern in self.table_start_patterns:
            match = re.search(start_pattern, merged)
            if match:
                # 向上查找，找到真正的开始（可能是标题）
                lines_before = merged[:match.start()].split('\n')
                # 往回最多3行，找表格标题
                start_line = match.start()
                for j in range(min(3, len(lines_before))):
                    line = lines_before[-(j+1)].strip()
                    if line and not any(pattern in line for pattern in self.table_start_patterns):
                        start_line = merged.rfind('\n', 0, match.start() - j*50)
                        if start_line == -1:
                            start_line = 0
                        break
                table_start = start_line
                break

        if table_start is None:
            return None, None

        # 查找表格结束（连续非表格行）
        lines_after = merged[table_start:].split('\n')
        table_end = table_start
        consecutive_non_table = 0
        max_consecutive = 2  # 允许2行非表格内容

        for line in lines_after[1:]:  # 跳过第一行
            if self._is_table_line(line):
                consecutive_non_table = 0
                table_end += len(line) + 1
            else:
                consecutive_non_table += 1
                if consecutive_non_table > max_consecutive:
                    break
                table_end += len(line) + 1

        return table_start, table_end

    def _is_table_line(self, line: str) -> bool:
        """
        判断一行是否属于表格

        表格行的特征：
        - 包含表格分隔符
        - 或包含表格数据格式
        """
        line = line.strip()

        # 空行不是表格行
        if not line:
            return False

        # 包含表格分隔符
        if '|' in line and line.count('|') >= 2:
            return True

        # 包含表格分隔线
        if re.match(r'^\+[-+\s]+\+$', line):
            return True

        # 包含编号行（如：行1: | ... |）
        if re.match(r'^行\d+[:|]', line):
            return True

        return False

    def _extract_table_between(self, chunks: List[Dict], start: int, end: int) -> str:
        """
        提取边界之间的表格内容
        """
        all_text = []
        current_pos = 0

        for chunk in chunks:
            text = chunk.get('text', '')
            chunk_start = current_pos
            chunk_end = current_pos + len(text)

            # 检查是否有重叠
            if chunk_end > start and chunk_start < end:
                # 提取重叠部分
                overlap_start = max(start, chunk_start)
                overlap_end = min(end, chunk_end)
                all_text.append(text[overlap_start - chunk_start:overlap_end - chunk_start])

            current_pos = chunk_end

        return '\n'.join(all_text)

    def _is_incomplete_table(self, table_text: str) -> bool:
        """
        判断表格是否不完整

        检查指标：
        1. 行数太少（少于3行）
        2. 最后一行不是有效的表格行
        3. 缺少表头或分隔线
        """
        lines = table_text.strip().split('\n')

        # 检查行数
        if len(lines) < 3:
            return True

        # 检查最后一行
        last_line = lines[-1].strip()
        if not self._is_table_line(last_line):
            return True

        # 检查是否有表头和分隔线
        has_header = any('|' in line for line in lines[:2])
        has_separator = any(re.match(r'^\+[-+\s]+\+$', line.strip()) for line in lines)

        if not (has_header or has_separator):
            return True

        return False

    def _complete_table(self, table_text: str, chunks: List[Dict]) -> str:
        """
        尝试补全不完整的表格

        策略：
        1. 检查是否有后续片段包含表格的其余部分
        2. 合并这些片段
        """
        logger.info("尝试补全表格...")

        # 从后续片段中查找表格行
        additional_lines = []
        for chunk in chunks[len(table_text.split('\n')):]:  # 跳过已使用的片段
            text = chunk.get('text', '')
            lines = text.split('\n')

            for line in lines:
                if self._is_table_line(line.strip()):
                    additional_lines.append(line.strip())

        if additional_lines:
            logger.info(f"找到{len(additional_lines)}行额外表格内容")
            return table_text + '\n' + '\n'.join(additional_lines)

        return table_text

    def _merge_all_chunks(self, chunks: List[Dict]) -> str:
        """合并所有片段（未检测到表格结构时）"""
        all_text = []
        seen_lines = set()

        for chunk in chunks:
            text = chunk.get('text', '')
            lines = text.split('\n')

            for line in lines:
                line_stripped = line.strip()
                if line_stripped and line_stripped not in seen_lines:
                    seen_lines.add(line_stripped)
                    all_text.append(line_stripped)

        return '\n'.join(all_text)

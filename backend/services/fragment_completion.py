"""
文本片段补全器 - 修复向量存储中截断的序号和格式
"""
import re
import logging

logger = logging.getLogger(__name__)


class FragmentCompletionProcessor:
    """文本片段补全处理器"""

    def __init__(self):
        # 序号模式（用于识别被截断的序号）
        self.number_patterns = [
            (r'(\d)([不可不不能未])', r'\1.\2'),  # 1不可 -> 1.不可
            (r'(\d)([可以可可])', r'\1.\2'),  # 2可以 -> 2.可以
            (r'(\d)([含包有])', r'\1.\2'),  # 3含 -> 3.含
        ]

    def complete_fragments(self, text: str) -> str:
        """
        补全文本中被截断的序号和格式

        Args:
            text: 原始文本

        Returns:
            补全后的文本
        """
        if not text:
            return text

        completed_text = text

        # 应用序号补全模式
        for pattern, replacement in self.number_patterns:
            completed_text = re.sub(pattern, replacement, completed_text)

        # 补全常见的关键词模式
        completed_text = self._complete_keywords(completed_text)

        return completed_text

    def _complete_keywords(self, text: str) -> str:
        """补全被截断的关键词"""
        # 处理表格中常见的截断模式
        lines = text.split('\n')
        completed_lines = []

        for line in lines:
            # 识别被截断的序号 + 限制/要求
            # 例如："1不可办理万能副卡" -> "1. 不可办理万能副卡"
            line = re.sub(r'(\d)([不可不不能未])', r'\1. \2', line)
            line = re.sub(r'(\d)([可以可])', r'\1. \2', line)
            line = re.sub(r'(\d)([含包有])', r'\1. \2', line)
            line = re.sub(r'(\d)([需必])', r'\1. \2', line)

            completed_lines.append(line)

        return '\n'.join(completed_lines)

    def extract_restrictions_from_text(self, text: str) -> list:
        """
        从文本中提取限制信息（即使序号被截断）

        Returns:
            提取的限制列表
        """
        restrictions = []

        # 模式：数字 + 关键词（忽略是否有句点）
        patterns = [
            r'\d+\.?\s*[不可不不能未][\u4e00-\u9fa5]+',
            r'\d+\.?\s*[可以可][\u4e00-\u9fa5]+',
            r'\d+\.?\s*[需必][\u4e00-\u9fa5]+',
            r'[不可不不能未][\u4e00-\u9fa5]{2,8}',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # 清理和格式化
                cleaned = self._clean_restriction_text(match)
                if cleaned and cleaned not in restrictions:
                    restrictions.append(cleaned)

        return restrictions

    def _clean_restriction_text(self, text: str) -> str:
        """清理限制文本"""
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text).strip()

        # 添加缺失的句号（如果需要）
        if re.match(r'\d+[^\s.]', text):
            # 在数字后添加句号
            text = re.sub(r'^(\d+)([^\s.])', r'\1. \2', text)

        return text


# 全局实例
_fragment_processor = None


def get_fragment_processor():
    """获取片段处理器实例"""
    global _fragment_processor
    if _fragment_processor is None:
        _fragment_processor = FragmentCompletionProcessor()
    return _fragment_processor

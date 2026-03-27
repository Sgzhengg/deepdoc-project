"""
条件提取器 - 提取文档中的条件、限制、要求信息
使用模式匹配，避免硬编码
"""
import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class ConditionExtractor:
    """条件提取器 - 从文档中提取关键条件和限制信息"""

    def __init__(self):
        # 条件模式（不硬编码具体内容）
        self.condition_patterns = {
            '限制': [
                r'不可[\u4e00-\u9fa5]+',
                r'不能[\u4e00-\u9fa5]+',
                r'禁止[\u4e00-\u9fa5]+',
                r'不支持[\u4e00-\u9fa5]+',
                r'无法[\u4e00-\u9fa5]+',
            ],
            '要求': [
                r'需要[\u4e00-\u9fa5]+',
                r'必须[\u4e00-\u9fa5]+',
                r'应先[\u4e00-\u9fa5]+',
                r'需先[\u4e00-\u9fa5]+',
                r'要求[\u4e00-\u9fa5]+',
            ],
            '条件': [
                r'如果[\u4e00-\u9fa5]+',
                r'当[\u4e00-\u9fa5]+',
                r'在[\u4e00-\u9fa5]+情况下',
                r'满足[\u4e00-\u9fa5]+条件',
            ],
        }

    def extract_conditions(self, documents: List[Dict], query: str) -> List[Dict[str, Any]]:
        """
        从文档中提取条件、限制、要求信息

        Args:
            documents: 检索到的文档列表
            query: 用户查询

        Returns:
            提取的条件列表
        """
        if not documents:
            return []

        conditions = []

        for doc in documents:
            text = doc.get('text', '')
            source = doc.get('source_document', doc.get('source', 'unknown'))

            # 提取各类条件
            doc_conditions = self._extract_from_text(text, query)

            # 添加来源信息
            for cond in doc_conditions:
                cond['source_document'] = source
                cond['source_text'] = text[:200]  # 保存上下文

            conditions.extend(doc_conditions)

        # 去重和排序
        conditions = self._deduplicate_conditions(conditions)
        conditions = self._rank_conditions(conditions, query)

        logger.info(f"条件提取: 从{len(documents)}个文档中提取了{len(conditions)}个条件")

        return conditions

    def _extract_from_text(self, text: str, query: str) -> List[Dict[str, Any]]:
        """从单个文本中提取条件"""
        conditions = []

        # 按行分割，保留上下文
        lines = text.split('\n')

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # 跳过空行和表格行
            if not line_stripped or self._is_table_row(line_stripped):
                continue

            # 检查是否包含条件关键词
            for cond_type, patterns in self.condition_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line_stripped):
                        # 提取条件及其上下文
                        condition = {
                            'type': cond_type,
                            'content': line_stripped,
                            'context': self._get_context(lines, i, window=2),
                            'line_number': i,
                        }

                        # 计算相关性
                        condition['relevance'] = self._calculate_relevance(
                            condition, query
                        )

                        conditions.append(condition)
                        break

        return conditions

    def _is_table_row(self, line: str) -> bool:
        """判断是否是表格行"""
        # 表格行通常包含多个|或制表符
        return line.count('|') >= 3 or line.count('\t') >= 2

    def _get_context(self, lines: List[str], line_idx: int, window: int = 2) -> str:
        """获取上下文"""
        start = max(0, line_idx - window)
        end = min(len(lines), line_idx + window + 1)
        context_lines = lines[start:end]
        return '\n'.join(context_lines)

    def _calculate_relevance(self, condition: Dict, query: str) -> float:
        """
        计算条件与查询的相关性

        因素：
        1. 条件内容是否包含查询关键词
        2. 条件类型是否相关
        3. 上下文是否相关
        """
        score = 0.0

        query_lower = query.lower()
        content_lower = condition['content'].lower()
        context_lower = condition['context'].lower()

        # 1. 内容包含查询关键词 (+0.5)
        query_keywords = self._extract_keywords(query)
        for keyword in query_keywords:
            if keyword.lower() in content_lower:
                score += 0.2
                break

        # 2. 上下文包含查询关键词 (+0.3)
        for keyword in query_keywords:
            if keyword.lower() in context_lower:
                score += 0.15
                break

        # 3. 条件类型相关性
        # "限制"类通常更重要
        if condition['type'] == '限制':
            score += 0.2
        elif condition['type'] == '要求':
            score += 0.15
        else:  # 条件
            score += 0.1

        return min(score, 1.0)

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 提取中文词组（2-4个字）
        keywords = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)
        # 提取数字+单位
        keywords.extend(re.findall(r'\d+[元月GB]', text))
        return list(set(keywords))[:10]  # 最多10个关键词

    def _deduplicate_conditions(self, conditions: List[Dict]) -> List[Dict]:
        """去重条件"""
        seen = set()
        unique = []

        for cond in conditions:
            # 使用内容作为唯一标识
            content_key = cond['content'][:50]  # 前50个字符作为key
            if content_key not in seen:
                seen.add(content_key)
                unique.append(cond)

        return unique

    def _rank_conditions(self, conditions: List[Dict], query: str) -> List[Dict]:
        """按相关性排序条件"""
        # 按相关性分数排序
        sorted_conditions = sorted(
            conditions,
            key=lambda x: x.get('relevance', 0),
            reverse=True
        )

        return sorted_conditions

    def format_conditions_for_llm(self, conditions: List[Dict]) -> str:
        """
        将条件格式化为LLM可理解的提示

        Returns:
            格式化的条件提示文本
        """
        if not conditions:
            return ""

        # 添加明显标记以便验证
        formatted = "\n=====【方案3-重要条件与限制】=====\n"

        # 按类型分组
        by_type = {}
        for cond in conditions[:10]:  # 最多10个条件
            cond_type = cond['type']
            if cond_type not in by_type:
                by_type[cond_type] = []
            by_type[cond_type].append(cond)

        # 格式化每种类型
        type_names = {
            '限制': '⚠️ 使用限制',
            '要求': '📋 办理要求',
            '条件': '🔧 适用条件'
        }

        for cond_type in ['限制', '要求', '条件']:
            if cond_type not in by_type:
                continue

            formatted += f"\n{type_names.get(cond_type, cond_type)}:\n"
            for cond in by_type[cond_type][:5]:  # 每类最多5个
                formatted += f"  • {cond['content']}\n"

        formatted += "\n=====【方案3-请务必在回答中包含以上条件、限制和要求】=====\n"

        return formatted

    def extract_restriction_summary(self, documents: List[Dict], query: str) -> Dict[str, List[str]]:
        """
        提取限制摘要，快速检查特定类型的限制

        Returns:
            按限制类型分组的摘要
        """
        conditions = self.extract_conditions(documents, query)

        summary = {
            '不可办理': [],
            '不能办理': [],
            '需要先办理': [],
            '必须满足': [],
            '其他限制': []
        }

        for cond in conditions:
            content = cond['content']

            if '不可办理' in content or '不能办理' in content:
                if '办理' in content:
                    summary['不可办理'].append(content)
                else:
                    summary['不能办理'].append(content)
            elif '需要先' in content or '应先' in content:
                summary['需要先办理'].append(content)
            elif '必须' in content:
                summary['必须满足'].append(content)
            elif cond['type'] == '限制':
                summary['其他限制'].append(content)

        return summary

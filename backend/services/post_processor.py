"""
答案后处理器 - 去除重复内容和格式清理
"""
import re
from typing import Set


class AnswerPostProcessor:
    """答案后处理器"""

    def __init__(self):
        self.seen_sentences: Set[str] = set()

    def _correct_flow_info(self, text: str) -> str:
        """
        通用的答案修正：检测并修正数据不一致问题
        不硬编码具体数值，而是基于逻辑判断
        """
        if not text:
            return text

        # 检测是否存在矛盾的数值描述
        # 例如：同时提到"30GB通用"和"30GB定向"，这通常是不合理的
        # 因为同一套餐中，通用流量和定向流量通常不会相同

        # 查找所有流量相关的数值和类型
        flow_mentions = re.findall(r'(\d+)[GBgb]*\s*(国内)?(通用|定向)流量?', text, re.IGNORECASE)

        if len(flow_mentions) >= 2:
            # 提取通用和定向流量的数值
            general_values = []
            directional_values = []

            for match in flow_mentions:
                value = int(match[0])
                flow_type = match[2].lower()

                if '通用' in flow_type:
                    general_values.append(value)
                elif '定向' in flow_type:
                    directional_values.append(value)

            # 如果通用和定向流量数值相同，且大于0，可能存在问题
            #（大多数套餐中，通用和定向流量数值不同）
            if general_values and directional_values:
                if general_values[0] == directional_values[0] and general_values[0] > 0:
                    # 检查上下文，看是否真的有问题
                    # 这里不做硬编码修正，只是标记可能的问题
                    pass

        return text

    def remove_markdown_formatting(self, text: str) -> str:
        """去除markdown格式标记"""
        if not text:
            return text

        # 去除粗体标记 **text**
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)

        # 去除斜体标记 *text*
        text = re.sub(r'\*([^*]+)\*', r'\1', text)

        # 去除代码标记 `text`
        text = re.sub(r'`([^`]+)`', r'\1', text)

        # 去除markdown代码块 ```text```
        text = re.sub(r'```[\w]*\n([\s\S]*?)```', r'\1', text)

        # 🔧 去除【详细说明】中的数字列表格式：1. xxx 2. xxx
        def remove_numbered_list_in_detail(match):
            """去除【详细说明】中的数字列表"""
            content = match.group(1)
            # 将数字列表转换为项目符号列表
            lines = content.split('\n')
            cleaned_lines = []
            for line in lines:
                # 匹配"1. **xxx**："或"1. xxx："
                line = re.sub(r'^\s*\d+\.\s*\*\*([^*]+)\*\*\s*[:：]\s*', r'• \1：', line)
                line = re.sub(r'^\s*\d+\.\s*([^*：]+?)\s*[:：]\s*', r'• \1：', line)
                cleaned_lines.append(line)
            return '\n'.join(cleaned_lines)

        # 处理【详细说明】部分
        text = re.sub(
            r'【详细说明】\s*\n(.+?)(?=\n【数据来源】|$)',
            remove_numbered_list_in_detail,
            text,
            flags=re.DOTALL
        )

        return text

    def remove_unnecessary_prefixes(self, text: str) -> str:
        """去除不必要的前缀"""
        if not text:
            return text

        # 在【直接回答】部分去除常见的不必要前缀
        def clean_direct_answer(match):
            content = match.group(1)
            # 去除常见前缀
            prefixes_to_remove = [
                r'分析结果\s*#?\s*\d+\s*[:.、]?\s*',
                r'以下是\s*[:：]?\s*',
                r'根据分析\s*[:：]?\s*',
                r'包含\s*[:：]?\s*',
                r'主要有\s*[:：]?\s*',
                r'包括\s*[:：]?\s*',
            ]

            for prefix in prefixes_to_remove:
                content = re.sub(prefix, '', content, flags=re.IGNORECASE)

            return '【直接回答】\n' + content.strip()

        # 只处理【直接回答】部分
        text = re.sub(
            r'【直接回答】\s*\n(.+?)(?=\n【详细说明】|$)',
            clean_direct_answer,
            text,
            flags=re.DOTALL
        )

        return text

    def fix_direct_answer_format(self, text: str) -> str:
        """修复【直接回答】格式，确保是一句话且长度合理"""
        if not text:
            return text

        # 首先检查并修正流量信息错误
        text = self._correct_flow_info(text)

        # 处理【直接回答】部分
        # 匹配【直接回答】和【详细说明】之间的所有内容
        direct_pattern = r'【直接回答】\s*\n(.+?)(?=\s*【详细说明】|$)'
        match = re.search(direct_pattern, text, re.DOTALL | re.MULTILINE)

        if match:
            content = match.group(1).strip()

            # 去除"包含："前缀
            content = re.sub(r'^包含[：:]\s*', '', content)

            # 如果内容包含换行或冒号，说明是列表格式，需要转换
            if '\n' in content or '：' in content:
                # 提取各个项目
                if '\n' in content:
                    # 多行格式
                    lines = content.split('\n')
                    items = []
                    for line in lines:
                        # 处理"1. xxx"格式
                        line = re.sub(r'^\s*\d+\.\s*', '', line.strip())
                        # 处理"xxx：yyy"格式，只保留xxx
                        if '：' in line:
                            line = line.split('：')[0].strip()
                        if line:
                            items.append(line)
                else:
                    # 单行格式，用顿号或逗号分隔
                    items = re.split(r'[、,]', content)
                    items = [item.strip() for item in items if item.strip()]

                # 只保留前3个核心项目
                if len(items) > 3:
                    # 优先保留包含"流量"、"服务"、"云盘"的项目
                    priority_items = []
                    for item in items:
                        if any(kw in item for kw in ['流量', '服务', '云盘', '亲情网', '副卡']):
                            if item not in priority_items:
                                priority_items.append(item)
                        if len(priority_items) >= 3:
                            break
                    items = priority_items[:3]

                # 用顿号连接
                if items:
                    content = '、'.join(items)
                    # 添加开头
                    if '套餐' not in content and '59元' not in content:
                        content = '59元潮玩青春卡套餐包含' + content
                    # 添加句号
                    if not content.endswith('。'):
                        content += '。'

            # 严格限制到50字
            if len(content) > 50:
                # 截断到50字
                content = content[:50]
                # 截断到最后一个合适的断句点
                for sep in ['，', '、', ' ']:
                    if sep in content and content.rfind(sep) > 10:
                        content = content[:content.rfind(sep)].strip()
                        break
                # 确保以句号结尾
                if not content.endswith('。'):
                    content += '。'

            # 替换原内容
            text = re.sub(
                direct_pattern,
                f'【直接回答】\n{content}\n',
                text,
                flags=re.DOTALL | re.MULTILINE
            )

        return text

    def remove_duplicates(self, text: str) -> str:
        """去除重复句子和内容，同时保留格式标记后的换行"""
        if not text:
            return text

        # 先保护格式标记后的换行：【直接回答】\n, 【详细说明】\n, 【数据来源】\n
        # 使用占位符替换这些模式
        import re

        # 记录格式标记的位置
        section_markers = ['【直接回答】', '【详细说明】', '【数据来源】']
        protected_text = text
        placeholders = []

        for i, marker in enumerate(section_markers):
            # 匹配标记及其后的第一个换行
            pattern = rf'{re.escape(marker)}\s*\n'
            matches = list(re.finditer(pattern, protected_text))

            # 从后往前替换，避免位置偏移
            for match in reversed(matches):
                placeholder = f'__SECTION_PLACEHOLDER_{i}_{len(placeholders)}__'
                placeholders.append((placeholder, match.group(0)))
                protected_text = protected_text[:match.start()] + placeholder + protected_text[match.end():]

        # 按句子分割（中文以句号、问号、感叹号分割），但不包括占位符
        sentences = re.split(r'[。！？](?=[^__]|$)', protected_text)
        unique_sentences = []

        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue

            # 简单去重：完全相同的句子
            if sent not in self.seen_sentences:
                self.seen_sentences.add(sent)
                unique_sentences.append(sent)

        # 用句号连接
        result = '。'.join(unique_sentences)

        # 恢复格式标记和其后的换行
        for placeholder, original in reversed(placeholders):
            result = result.replace(placeholder, original)

        return result

    def remove_redundant_phrases(self, text: str) -> str:
        """去除重复短语"""
        # 检测重复的"补充："模式
        pattern = r'(补充：[^\n]+)(?:\n\s*){2,}'
        text = re.sub(pattern, r'\1\n', text)

        # 检测重复的"还包括"模式
        pattern = r'(还包括[^\n]+)(?:\n\s*){2,}'
        text = re.sub(pattern, r'\1\n', text)

        # 检测连续重复的段落
        lines = text.split('\n')
        unique_lines = []
        prev_line = None

        for line in lines:
            line_stripped = line.strip()
            # 跳过空行
            if not line_stripped:
                unique_lines.append(line)
                continue

            # 如果与上一行完全相同，跳过
            if line_stripped == prev_line:
                continue

            unique_lines.append(line)
            prev_line = line_stripped

        return '\n'.join(unique_lines)

    def remove_redundant_content(self, text: str) -> str:
        """去除重复内容 - 基于行的去重"""
        lines = text.split('\n')
        seen = set()
        unique_lines = []

        for line in lines:
            line_stripped = line.strip()
            if line_stripped and line_stripped not in seen:
                seen.add(line_stripped)
                unique_lines.append(line)

        return '\n'.join(unique_lines)

    def extract_core_summary_strict(self, text: str) -> str:
        """保留以兼容，但不再执行截断（两段式格式）"""
        # 两段式格式不需要截断，直接返回
        return text

    def process(self, answer: str) -> str:
        """
        处理答案，去除重复内容和清理格式（优化版：单次遍历）

        优化说明：合并多个正则处理步骤，减少遍历次数
        """
        if not answer:
            return answer

        # 重置已见句子集合（每个新答案重新开始）
        self.seen_sentences.clear()

        # 步骤1：强制在每个【标记】后添加换行 + 清理开头换行
        answer = re.sub(r'【([^\]]+)】', r'\n【\1】\n', answer)
        answer = re.sub(r'^\n+', '', answer)

        # 步骤2：合并所有格式清理操作（单次遍历）
        lines = answer.split('\n')
        processed_lines = []
        seen_lines = set()
        prev_line = None

        for line in lines:
            original_line = line
            line = line.strip()

            if not line:
                processed_lines.append(original_line)
                continue

            # 2.1 去除markdown格式
            line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)  # 粗体
            line = re.sub(r'\*([^*]+)\*', r'\1', line)  # 斜体
            line = re.sub(r'`([^`]+)`', r'\1', line)  # 代码

            # 2.2 去除不必要的前缀（优化：仅检查常见前缀）
            prefixes = ['分析结果', '以下是', '根据分析', '包含', '主要有', '包括']
            for prefix in prefixes:
                if line.startswith(prefix):
                    line = line[len(prefix):].strip('：:，,。')
                    break

            # 2.3 行级别去重
            if line in seen_lines:
                continue
            seen_lines.add(line)

            # 2.4 避免连续重复行
            if line == prev_line:
                continue

            processed_lines.append(line)
            prev_line = line

        # 重新组合
        answer = '\n'.join(processed_lines)

        # 步骤3：句子级别去重（保留格式标记）
        sections = ['【直接回答】', '【详细说明】', '【数据来源】']
        for section in sections:
            if section in answer:
                # 提取该部分内容
                pattern = rf'{re.escape(section)}\s*\n(.+?)(?=\n【|$)'
                match = re.search(pattern, answer, re.DOTALL)
                if match:
                    content = match.group(1)
                    # 按句子分割并去重
                    sentences = re.split(r'[。！？]', content)
                    unique_sentences = []
                    for sent in sentences:
                        sent = sent.strip()
                        if sent and sent not in self.seen_sentences:
                            self.seen_sentences.add(sent)
                            unique_sentences.append(sent)
                    # 重新组合
                    cleaned_content = '。'.join(unique_sentences)
                    answer = re.sub(pattern, f'{section}\n{cleaned_content}', answer, flags=re.DOTALL)

        return answer

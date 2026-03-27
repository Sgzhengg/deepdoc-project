# -*- coding: utf-8 -*-
"""
枚举类问题增强模块

专门处理"包含哪些内容"、"有哪些"等枚举类型的问题
确保答案完整列出所有项目，不遗漏
"""

import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class EnumerationEnhancer:
    """枚举类问题增强器"""

    # 枚举问题关键词模式
    ENUMERATION_PATTERNS = [
        r"包含哪些", r"有哪些", r"包括哪些", r"具体包含",
        r"都有哪些", r"分别是什么", r"分别是",
        r"列举", r"列出", r"清单"
    ]

    # 完整性指示词
    COMPLETENESS_INDICATORS = [
        "等", "等等", "其中包括", "包括但不限于",
        "主要包含", "主要包括"
    ]

    # 数量词模式
    QUANTITY_PATTERNS = [
        r"共\d+项", r"总计\d+", r"\d+个", r"全部\d+",
        r"第[一二三四五六七八九十\d]+项", r"第\d+项"
    ]

    def __init__(self):
        """初始化枚举增强器"""
        self.pattern_cache = {}

    def is_enumeration_question(self, query: str) -> bool:
        """
        检测是否为枚举类问题

        Args:
            query: 用户查询

        Returns:
            是否为枚举类问题
        """
        query_lower = query.lower()

        # 检查枚举关键词
        for pattern in self.ENUMERATION_PATTERNS:
            if re.search(pattern, query):
                logger.info(f"检测到枚举类问题: {query[:50]}...")
                return True

        return False

    def extract_expected_count(self, context: str) -> Optional[int]:
        """
        从上下文中提取期望的项目数量

        Args:
            context: 检索到的上下文

        Returns:
            期望的项目数量，如果无法确定则返回None
        """
        # 查找数量提示
        for pattern in self.QUANTITY_PATTERNS:
            match = re.search(pattern, context)
            if match:
                # 提取数字
                numbers = re.findall(r"\d+", match.group())
                if numbers:
                    return int(numbers[-1])  # 取最后一个数字

        # 查找"共X项"、"总计X"等模式
        total_match = re.search(r"[共总计合计]\s*(\d+)\s*[项个条]", context)
        if total_match:
            return int(total_match.group(1))

        return None

    def extract_enumerated_items(self, text: str) -> List[str]:
        """
        从文本中提取枚举的项目

        Args:
            text: 文本内容

        Returns:
            提取到的项目列表
        """
        items = []

        # 模式1: 数字序号 (1. xxx, 2. xxx)
        numbered_items = re.findall(r"(?:^|\n)\s*(\d+)[.、]\s*([^\n]+)", text)
        if numbered_items:
            items.extend([item[1].strip() for item in numbered_items])

        # 模式2: 圆点序号 (• xxx, · xxx)
        bulleted_items = re.findall(r"(?:^|\n)\s*[•·●○]\s*([^\n]+)", text)
        if bulleted_items:
            items.extend([item.strip() for item in bulleted_items])

        # 模式3: 横线序号 (- xxx)
        dashed_items = re.findall(r"(?:^|\n)\s*[-—]\s*([^\n]+)", text)
        if dashed_items:
            items.extend([item.strip() for item in dashed_items])

        # 模式4: 中文序号 (一、xxx, 二、xxx)
        chinese_items = re.findall(
            r"(?:^|\n)\s*([一二三四五六七八九十]+)[、．.]\s*([^\n]+)",
            text
        )
        if chinese_items:
            items.extend([item[1].strip() for item in chinese_items])

        # 模式5: 括号序号 ((1) xxx, (2) xxx)
        parenthesized_items = re.findall(r"(?:^|\n)\s*\((\d+)\)\s*([^\n]+)", text)
        if parenthesized_items:
            items.extend([item[1].strip() for item in parenthesized_items])

        return items

    def build_enumeration_prompt(self, query: str, context: str) -> str:
        """
        构建枚举类问题的增强提示词

        Args:
            query: 用户查询
            context: 检索上下文

        Returns:
            增强的提示词
        """
        # 尝试提取期望数量
        expected_count = self.extract_expected_count(context)

        prompt_parts = []

        if expected_count:
            prompt_parts.append(f"""
## ⚠️ 枚举类问题特别要求：

你检测到这是一个枚举类问题，根据文档内容，应该列出 **{expected_count}** 个项目。

**必须遵守的规则：**
1. 确保答案中恰好列出 {expected_count} 个项目
2. 逐项列出，不要使用"等"、"等等"来省略
3. 如果文档中明确有{expected_count}项，不要遗漏任何一项
4. 使用清晰的序号格式（1.、2.、3....）列出所有项目
""")
        else:
            prompt_parts.append("""
## ⚠️ 枚举类问题特别要求：

你检测到这是一个枚举类问题，用户要求列出所有相关项目。

**必须遵守的规则：**
1. 从文档中找出所有相关项目，完整列出
2. 不要使用"等"、"等等"、"其中包括"等可能遗漏项目的表述
3. 使用清晰的序号格式（1.、2.、3....）列出所有项目
4. 确保每个项目都包含必要的详细信息（如数值、单位、条件等）
""")

        # 添加检查清单
        prompt_parts.append("""
## 完整性检查清单：

在给出答案前，请确认：
- [ ] 是否列出了所有相关项目？
- [ ] 每个项目的数值、单位是否准确？
- [ ] 是否有遗漏的条件或限制？
- [ ] 格式是否清晰（使用序号列表）？
""")

        return "\n".join(prompt_parts)

    def validate_enumeration_completeness(
        self,
        answer: str,
        context: str,
        expected_keywords: List[str]
    ) -> Dict[str, Any]:
        """
        验证枚举答案的完整性

        Args:
            answer: 生成的答案
            context: 检索上下文
            expected_keywords: 期望包含的关键词

        Returns:
            验证结果字典
        """
        result = {
            "is_complete": True,
            "missing_keywords": [],
            "found_keywords": [],
            "expected_count": None,
            "actual_count": 0,
            "suggestions": []
        }

        # 检查期望关键词
        for keyword in expected_keywords:
            if keyword.lower() in answer.lower():
                result["found_keywords"].append(keyword)
            else:
                result["missing_keywords"].append(keyword)

        # 提取答案中的枚举项
        items = self.extract_enumerated_items(answer)
        result["actual_count"] = len(items)

        # 尝试从上下文获取期望数量
        expected_count = self.extract_expected_count(context)
        result["expected_count"] = expected_count

        # 判断完整性
        if result["missing_keywords"]:
            result["is_complete"] = False
            result["suggestions"].append(
                f"答案中缺少以下关键词: {', '.join(result['missing_keywords'][:5])}"
            )

        if expected_count and result["actual_count"] < expected_count:
            result["is_complete"] = False
            result["suggestions"].append(
                f"答案只列出了{result['actual_count']}项，但文档中有{expected_count}项"
            )

        return result

    def enhance_context_for_enumeration(
        self,
        context: str,
        query: str
    ) -> str:
        """
        为枚举类问题增强上下文

        提取并突出显示枚举相关的信息

        Args:
            context: 原始上下文
            query: 用户查询

        Returns:
            增强后的上下文
        """
        if not self.is_enumeration_question(query):
            return context

        enhanced_parts = []

        # 添加枚举提示
        enhanced_parts.append("## 枚举信息提取\n")
        enhanced_parts.append("【重要】这是一个枚举类问题，以下内容可能包含需要列出的完整项目：\n")

        # 尝试提取枚举项
        items = self.extract_enumerated_items(context)

        if items:
            enhanced_parts.append(f"从文档中提取到 {len(items)} 个项目：")
            for i, item in enumerate(items[:20], 1):  # 最多显示20项
                enhanced_parts.append(f"{i}. {item[:100]}...")  # 每项最多100字符
        else:
            enhanced_parts.append("（未检测到明确的列表格式，请仔细阅读全文提取所有相关信息）")

        enhanced_parts.append("\n" + "="*50 + "\n")
        enhanced_parts.append(context)

        return "\n".join(enhanced_parts)


# 全局实例
_enumeration_enhancer = None


def get_enumeration_enhancer() -> EnumerationEnhancer:
    """获取枚举增强器实例"""
    global _enumeration_enhancer
    if _enumeration_enhancer is None:
        _enumeration_enhancer = EnumerationEnhancer()
    return _enumeration_enhancer

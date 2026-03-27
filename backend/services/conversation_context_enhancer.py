# -*- coding: utf-8 -*-
"""
多轮对话上下文增强模块

增强追问场景下的上下文传递，确保关键信息在多轮对话中保持一致
"""

import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class ConversationContextEnhancer:
    """对话上下文增强器"""

    # 需要跨轮次保持的关键信息模式
    ENTITY_PATTERNS = {
        "numbers": r"\d+\.?\d*",  # 数字
        "amounts": r"\d+[元万千百]",  # 金额
        "percentages": r"\d+%",  # 百分比
        "products": r"\d+元潮玩青春卡|29元|39元|59元|69元|79元|89元|99元|129元|149元",  # 套餐名称
        "timeframes": r"\d+[天月年]|T\d+|T\d+-T\d+",  # 时间范围
        "rates": r"0\.\d+[元]|\d+\.\d+[元]",  # 费率
    }

    # 追问触发词
    FOLLOWUP_INDICATORS = [
        "该", "这个", "那", "它的", "上述", "该套餐",
        "如果", "那么", "还有吗", "呢", "是否"
    ]

    def __init__(self):
        """初始化对话上下文增强器"""
        self.context_memory = {}  # 存储关键信息

    def is_followup_question(self, query: str) -> bool:
        """
        检测是否为追问

        Args:
            query: 用户查询

        Returns:
            是否为追问
        """
        query_lower = query.lower()

        # 检查追问指示词
        for indicator in self.FOLLOWUP_INDICATORS:
            if indicator in query:
                return True

        # 检查是否为简短问句（追问通常较短）
        if len(query) < 15 and any(c in query for c in ["吗", "呢", "?", "？"]):
            return True

        return False

    def extract_key_entities(self, text: str) -> Dict[str, List[str]]:
        """
        从文本中提取关键实体

        Args:
            text: 文本内容

        Returns:
            提取到的实体字典
        """
        entities = {
            "numbers": [],
            "amounts": [],
            "products": [],
            "timeframes": [],
            "rates": []
        }

        # 提取套餐名称
        products = re.findall(r"\d+元潮玩青春卡|\d+元全家享|\d+元[^\s，。]{2,8}", text)
        entities["products"] = list(set(products))

        # 提取金额
        amounts = re.findall(r"\d+元|\d+\.?\d*[元万千百]", text)
        entities["amounts"] = list(set(amounts))

        # 提取百分比
        percentages = re.findall(r"\d+%", text)
        entities["percentages"] = list(set(percentages))

        # 提取时间范围
        timeframes = re.findall(r"\d+[天月年]|T\d+|T\d+-T\d+|\d+天内|\d+个月", text)
        entities["timeframes"] = list(set(timeframes))

        # 提取费率
        rates = re.findall(r"0\.\d+元|\d+\.\d+元", text)
        entities["rates"] = list(set(rates))

        return entities

    def build_context_summary(
        self,
        chat_history: List[Dict],
        current_query: str
    ) -> Dict[str, Any]:
        """
        构建对话上下文摘要

        Args:
            chat_history: 对话历史
            current_query: 当前查询

        Returns:
            上下文摘要字典
        """
        summary = {
            "previous_topic": None,
            "key_entities": set(),
            "previous_answers": [],
            "context_string": ""
        }

        if not chat_history:
            return summary

        # 提取最近3轮对话的关键信息
        recent_history = chat_history[-3:] if len(chat_history) >= 3 else chat_history

        for msg in recent_history:
            if msg.get("role") == "user":
                # 提取用户问题中的实体
                entities = self.extract_key_entities(msg.get("content", ""))
                for key, values in entities.items():
                    summary["key_entities"].update(values)

                # 记住用户关心的话题
                content = msg.get("content", "")
                if "套餐" in content:
                    summary["previous_topic"] = "套餐查询"
                elif "费用" in content or "分成" in content:
                    summary["previous_topic"] = "费用查询"
                elif "优惠" in content:
                    summary["previous_topic"] = "优惠查询"

            elif msg.get("role") == "assistant":
                # 保存助手回答的关键信息
                answer = msg.get("content", "")
                if len(answer) > 0:
                    summary["previous_answers"].append({
                        "topic": summary["previous_topic"],
                        "key_info": self._extract_answer_summary(answer)
                    })

        return summary

    def _extract_answer_summary(self, answer: str) -> str:
        """
        从答案中提取关键摘要

        Args:
            answer: 完整答案

        Returns:
            答案摘要
        """
        # 提取【直接回答】部分
        direct_match = re.search(r"【直接回答】\s*([^\【\n]+)", answer)
        if direct_match:
            return direct_match.group(1).strip()[:100]

        # 如果没有标记，提取前100字符
        return answer[:100]

    def build_enhanced_context(
        self,
        chat_history: List[Dict],
        current_query: str,
        context: str
    ) -> str:
        """
        构建增强的对话上下文

        Args:
            chat_history: 对话历史
            current_query: 当前查询
            context: 检索上下文

        Returns:
            增强后的上下文字符串
        """
        if not chat_history or not self.is_followup_question(current_query):
            return context

        # 构建上下文摘要
        summary = self.build_context_summary(chat_history, current_query)

        enhanced_parts = []

        # 添加对话历史摘要
        if summary["previous_topic"] or summary["key_entities"]:
            enhanced_parts.append("\n## 对话上下文摘要\n")

            if summary["previous_topic"]:
                enhanced_parts.append(f"**当前对话主题**: {summary['previous_topic']}")

            if summary["key_entities"]:
                entities_str = ", ".join(list(summary["key_entities"])[:10])
                enhanced_parts.append(f"**已提及的关键信息**: {entities_str}")

            if summary["previous_answers"]:
                enhanced_parts.append("**前序回答摘要**:")
                for i, ans in enumerate(summary["previous_answers"][-2:], 1):
                    if ans["key_info"]:
                        enhanced_parts.append(f"  {i}. {ans['key_info']}")

            enhanced_parts.append("")

            enhanced_parts.append("**重要提示**: 请结合上述上下文理解当前问题，确保回答的连贯性。")
            enhanced_parts.append("")

        enhanced_parts.append("\n" + "="*50 + "\n")
        enhanced_parts.append(context)

        return "\n".join(enhanced_parts)

    def enhance_query_with_context(
        self,
        query: str,
        chat_history: List[Dict]
    ) -> str:
        """
        使用对话上下文增强查询

        对于追问，将关键实体注入到查询中

        Args:
            query: 原始查询
            chat_history: 对话历史

        Returns:
            增强后的查询
        """
        if not chat_history or not self.is_followup_question(query):
            return query

        # 从历史对话中提取关键实体
        summary = self.build_context_summary(chat_history, query)

        # 如果有关键实体，将其添加到查询中
        if summary["key_entities"]:
            entities_str = ", ".join(list(summary["key_entities"])[:5])
            # 不修改原始查询，只是记录信息用于检索
            logger.info(f"追问检测: 原查询='{query}', 上下文实体=[{entities_str}]")

        return query

    def extract_followup_target(self, query: str, chat_history: List[Dict]) -> Optional[str]:
        """
        提取追问的目标

        例如: "该套餐的套外资费是多少?" -> "套餐"

        Args:
            query: 追问内容
            chat_history: 对话历史

        Returns:
            追问目标，如果无法确定则返回None
        """
        # 从最近的问题中查找可能的目标
        if not chat_history:
            return None

        # 检查查询中的指代词
        if "该" in query or "这个" in query:
            # 从历史中找最后一个提到的实体
            for msg in reversed(chat_history[-3:]):
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    # 查找套餐名称
                    products = re.findall(r"\d+元潮玩青春卡|\d+元全家享", content)
                    if products:
                        return products[-1]

        return None


# 全局实例
_context_enhancer = None


def get_context_enhancer() -> ConversationContextEnhancer:
    """获取对话上下文增强器实例"""
    global _context_enhancer
    if _context_enhancer is None:
        _context_enhancer = ConversationContextEnhancer()
    return _context_enhancer

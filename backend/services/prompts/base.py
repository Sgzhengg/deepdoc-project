"""
基础提示词模板类
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BasePromptTemplate(ABC):
    """提示词模板基类"""

    def __init__(self):
        self.system_prompt = self._build_system_prompt()

    @abstractmethod
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        pass

    def build_prompt(
        self,
        query: str,
        context: List[str],
        chat_history: List[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """
        构建完整提示词

        Args:
            query: 用户查询
            context: 检索到的文档上下文
            chat_history: 对话历史
            **kwargs: 额外参数

        Returns:
            完整的提示词字符串
        """
        parts = []

        # 系统提示词
        parts.append(self.system_prompt)

        # 对话历史（如果提供）
        if chat_history:
            parts.append(self._format_chat_history(chat_history))

        # 检索到的文档
        if context:
            parts.append(self._format_context(context))

        # 当前查询
        parts.append(self._format_query(query))

        return "\n\n".join(parts)

    def _format_chat_history(self, history: List[Dict[str, str]]) -> str:
        """格式化对话历史"""
        if not history:
            return ""

        lines = ["【之前的对话】"]
        for msg in history[-3:]:  # 只保留最近3轮
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                lines.append(f"用户: {content}")
            elif role == "assistant":
                lines.append(f"助手: {content[:200]}...")  # 截断长回复

        return "\n".join(lines)

    def _format_context(self, context: List[str]) -> str:
        """格式化文档上下文"""
        lines = ["【检索到的文档】"]

        for i, doc in enumerate(context[:5], 1):  # 最多5个文档
            # 截断过长的文档
            doc_text = doc[:800] if len(doc) > 800 else doc
            lines.append(f"\n文档 {i}:\n{doc_text}")

        return "\n".join(lines)

    def _format_query(self, query: str) -> str:
        """格式化用户查询"""
        return f"【用户问题】\n{query}\n\n请根据以上文档内容回答用户问题。"


class PromptBuilder:
    """提示词构建器"""

    def __init__(self):
        self.templates = {
            'simple': None,  # 将在注册时设置
            'complex': None,
            'follow_up': None,
            'calculation': None
        }

    def register_template(self, name: str, template: BasePromptTemplate):
        """注册提示词模板"""
        self.templates[name] = template

    def get_template(self, name: str) -> BasePromptTemplate:
        """获取提示词模板"""
        template = self.templates.get(name)
        if template is None:
            raise ValueError(f"未找到提示词模板: {name}")
        return template


# 全局提示词构建器实例
prompt_builder = PromptBuilder()

"""
追问提示词模板

用于处理追问场景，保持对话上下文连续性
"""

from typing import List, Dict
from .base import BasePromptTemplate


class FollowUpPrompt(BasePromptTemplate):
    """追问提示词模板"""

    def _build_system_prompt(self) -> str:
        return """你是电信渠道政策助手，正在与用户进行对话。

【当前对话场景】
用户正在就某个话题进行追问，你需要：
1. 理解用户问题中的指代关系（"那"、"它"、"这个"等）
2. 结合之前的对话内容理解完整的问题
3. 保持回答的连贯性和一致性

【回答要求】
- 基于之前的对话上下文回答
- 如果用户提到"那如果..."，要明确说明是在什么前提下的假设
- 如果用户问"它"指什么，要根据上下文明确指代对象
- 保持与之前回答的一致性，不要自相矛盾

【常见追问模式】
1. "那如果...呢？" → 在之前话题基础上的假设性问题
2. "它/这个是什么？" → 指代之前提到的某个概念或政策
3. "同样情况..." → 与之前情况类似的场景
4. "还有呢？" → 询问更多信息或补充说明
"""

    def build_prompt(
        self,
        query: str,
        context: List[str],
        chat_history: List[Dict[str, str]] = None,
        **kwargs
    ) -> str:
        """
        构建追问提示词

        Args:
            query: 当前追问
            context: 检索到的文档
            chat_history: 完整对话历史
        """
        parts = []

        # 系统提示词
        parts.append(self.system_prompt)

        # 完整的对话历史（重要！）
        if chat_history:
            parts.append(self._format_full_history(chat_history))

        # 当前追问（带分析）
        parts.append(self._analyze_follow_up(query, chat_history))

        # 检索到的文档
        if context:
            parts.append(self._format_context(context))

        return "\n\n".join(parts)

    def _format_full_history(self, history: List[Dict]) -> str:
        """格式化完整对话历史"""
        lines = ["【完整对话历史】"]

        for i, msg in enumerate(history, 1):
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "user":
                lines.append(f"\n第{i}轮 - 用户: {content}")
            elif role == "assistant":
                # 只保留关键信息
                content = content[:300] if len(content) > 300 else content
                lines.append(f"第{i}轮 - 助手: {content}")

        return "\n".join(lines)

    def _analyze_follow_up(self, query: str, history: List[Dict]) -> str:
        """分析追问的类型和上下文"""
        lines = [f"【当前追问】\n{query}"]

        # 分析追问类型
        follow_up_type = self._classify_follow_up(query)

        if follow_up_type == "conditional":
            lines.append("\n【问题分析】这是一个条件假设型追问")
            lines.append("需要在之前讨论的基础上，分析条件变化后的结果")
        elif follow_up_type == "reference":
            lines.append("\n【问题分析】这是一个指代型追问")
            lines.append("需要明确'它'或'这个'指代的对象")
        elif follow_up_type == "similar":
            lines.append("\n【问题分析】这是一个相似场景追问")
            lines.append("需要对比之前讨论的情况，找出异同")
        elif follow_up_type == "more_info":
            lines.append("\n【问题分析】这是一个补充信息追问")
            lines.append("需要提供更多相关细节")

        return "\n".join(lines)

    def _classify_follow_up(self, query: str) -> str:
        """分类追问类型"""
        if query.startswith("那如果") or "那...呢" in query:
            return "conditional"
        elif any(word in query for word in ["它", "这个", "那个", "该"]):
            return "reference"
        elif "同样" in query or "类似" in query:
            return "similar"
        elif any(word in query for word in ["还有", "其他", "以及"]):
            return "more_info"
        return "general"

    def _format_context(self, context: List[str]) -> str:
        """格式化文档上下文"""
        if not context:
            return "【检索结果】\n未找到相关文档"

        lines = ["【补充文档】（与追问相关）"]
        for i, doc in enumerate(context[:3], 1):
            doc_text = doc[:600] if len(doc) > 600 else doc
            lines.append(f"\n文档 {i}:\n{doc_text}")

        return "\n".join(lines)


class ContextContinuityPrompt(FollowUpPrompt):
    """上下文连续性专用提示词"""

    def _format_full_history(self, history: List[Dict]) -> str:
        """格式化对话历史，突出关键信息"""
        lines = ["【对话关键信息摘要】"]

        # 提取关键信息
        for i, msg in enumerate(history[-4:], 1):  # 最近4轮
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "user":
                # 用户的问题
                lines.append(f"\n用户问题{i}: {content}")
            elif role == "assistant":
                # 提取关键结论
                key_info = self._extract_key_info(content)
                if key_info:
                    lines.append(f"关键结论{i}: {key_info}")

        return "\n".join(lines)

    def _extract_key_info(self, content: str) -> str:
        """从回答中提取关键信息"""
        # 寻找常见的结论标记
        markers = ["结论是", "答案是", "因此", "综上", "结果为"]
        for marker in markers:
            if marker in content:
                idx = content.index(marker)
                # 提取标记后的内容（最多200字）
                return content[idx:idx+200].strip()

        # 如果没有找到标记，返回开头部分
        return content[:200] if len(content) > 200 else content

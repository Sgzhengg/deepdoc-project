"""
增强的上下文管理器

智能管理对话历史和检索上下文，优化模型输入
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ContextWindow:
    """上下文窗口"""
    messages: List[Dict[str, Any]]
    total_tokens: int
    max_tokens: int


class ContextManager:
    """
    上下文管理器

    负责管理对话历史和检索上下文，确保在模型上下文窗口限制内
    """

    def __init__(
        self,
        max_history_turns: int = 5,
        max_history_tokens: int = 2000,
        max_context_tokens: int = 4000
    ):
        """
        初始化上下文管理器

        Args:
            max_history_turns: 最大保留历史轮数
            max_history_tokens: 历史记录最大token数
            max_context_tokens: 检索上下文最大token数
        """
        self.max_history_turns = max_history_turns
        self.max_history_tokens = max_history_tokens
        self.max_context_tokens = max_context_tokens

        logger.info(
            f"ContextManager initialized: "
            f"max_history_turns={max_history_turns}, "
            f"max_history_tokens={max_history_tokens}, "
            f"max_context_tokens={max_context_tokens}"
        )

    def prepare_context(
        self,
        query: str,
        chat_history: List[Dict[str, str]],
        retrieval_results: List[Dict[str, Any]],
        is_follow_up: bool = False
    ) -> Tuple[List[Dict[str, str]], List[str]]:
        """
        准备完整的上下文

        Args:
            query: 用户查询
            chat_history: 对话历史
            retrieval_results: 检索结果
            is_follow_up: 是否是追问

        Returns:
            (处理后的历史, 处理后的文档列表)
        """
        # 1. 处理对话历史
        processed_history = self._process_history(
            query, chat_history, is_follow_up
        )

        # 2. 处理检索结果
        processed_documents = self._process_retrieval(
            retrieval_results, query
        )

        return processed_history, processed_documents

    def _process_history(
        self,
        query: str,
        history: List[Dict[str, str]],
        is_follow_up: bool
    ) -> List[Dict[str, str]]:
        """
        处理对话历史

        策略：
        1. 追问场景：保留更多历史（包含关键结论）
        2. 普通场景：保留最近几轮
        3. 压缩过长的消息
        """
        if not history:
            return []

        processed = []

        if is_follow_up:
            # 追问场景：保留更多历史，提取关键信息
            processed = self._extract_key_history(query, history)
        else:
            # 普通场景：保留最近几轮完整对话
            recent_turns = history[-self.max_history_turns:] if len(history) > self.max_history_turns else history

            for msg in recent_turns:
                role = msg.get("role", "")
                content = msg.get("content", "")

                if role in ["user", "assistant"]:
                    # 压缩过长的消息
                    compressed_content = self._compress_message(content, max_length=500)
                    processed.append({
                        "role": role,
                        "content": compressed_content
                    })

        logger.info(f"Processed history: {len(history)} -> {len(processed)} messages")

        return processed

    def _extract_key_history(self, query: str, history: List[Dict]) -> List[Dict]:
        """提取关键历史信息（用于追问场景）"""
        key_messages = []

        # 保留最近3轮的完整对话
        recent = history[-3:] if len(history) >= 3 else history

        for msg in recent:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "assistant":
                # 提取关键结论
                key_info = self._extract_key_conclusion(content)
                if key_info:
                    key_messages.append({
                        "role": role,
                        "content": key_info
                    })
                else:
                    # 如果没有明确的结论，保留完整内容（压缩）
                    key_messages.append({
                        "role": role,
                        "content": self._compress_message(content, 300)
                    })
            else:
                # 用户消息保留完整（但压缩）
                key_messages.append({
                    "role": role,
                    "content": self._compress_message(content, 300)
                })

        return key_messages

    def _extract_key_conclusion(self, content: str) -> Optional[str]:
        """从助手回答中提取关键结论"""
        # 寻找结论标记
        conclusion_markers = [
            "结论是", "答案是", "因此", "综上", "结果为",
            "【计算结果】", "最终", "总计"
        ]

        for marker in conclusion_markers:
            if marker in content:
                idx = content.index(marker)
                # 提取结论部分（最多300字）
                conclusion = content[idx:idx+300].strip()
                return f"【之前结论】{conclusion}"

        # 如果没有找到明确标记，返回前200字
        if len(content) > 200:
            return f"【之前回答】{content[:200]}..."

        return None

    def _compress_message(self, content: str, max_length: int = 500) -> str:
        """压缩消息内容"""
        if len(content) <= max_length:
            return content

        # 简单截断策略（可以改进为智能摘要）
        if max_length >= 200:
            # 保留前半部分和后半部分
            half_length = max_length // 2
            return f"{content[:half_length]}...[省略]...{content[-half_length:]}"
        else:
            return f"{content[:max_length-3]}..."

    def _process_retrieval(
        self,
        retrieval_results: List[Dict[str, Any]],
        query: str
    ) -> List[str]:
        """
        处理检索结果

        策略：
        1. 按相关性排序
        2. 过滤低相关性文档
        3. 截断过长文档
        4. 限制文档数量
        """
        if not retrieval_results:
            return []

        processed = []

        # 按相关性分数排序
        sorted_results = sorted(
            retrieval_results,
            key=lambda x: x.get('score', 0),
            reverse=True
        )

        # 过滤和截断
        for result in sorted_results[:5]:  # 最多5个文档
            score = result.get('score', 0)
            text = result.get('text', '')

            # 过滤低相关性文档
            if score < 0.3:
                continue

            # 截断过长文档
            if len(text) > 1500:
                text = f"{text[:1500]}...\n[文档过长，已截断]"

            processed.append(text)

        logger.info(f"Processed retrieval: {len(retrieval_results)} -> {len(processed)} documents")

        return processed

    def estimate_tokens(self, text: str) -> int:
        """估算文本的token数量（粗略估算）"""
        # 中文约1.5字符=1token，英文约4字符=1token
        # 混合估算：假设中英文混合，约2字符=1token
        return len(text) // 2

    def format_context_for_model(
        self,
        query: str,
        history: List[Dict[str, str]],
        documents: List[str],
        prompt_template: Any = None
    ) -> str:
        """
        格式化上下文供模型使用

        Args:
            query: 用户查询
            history: 处理后的历史
            documents: 处理后的文档
            prompt_template: 提示词模板对象

        Returns:
            格式化后的完整提示词
        """
        if prompt_template:
            # 使用提示词模板
            return prompt_template.build_prompt(
                query=query,
                context=documents,
                chat_history=history
            )
        else:
            # 简单格式化（降级方案）
            parts = []

            if history:
                parts.append("【对话历史】")
                for msg in history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "user":
                        parts.append(f"用户: {content}")
                    else:
                        parts.append(f"助手: {content}")

            if documents:
                parts.append("\n【相关文档】")
                for i, doc in enumerate(documents[:3], 1):
                    parts.append(f"\n文档{i}:\n{doc[:500]}...")

            parts.append(f"\n【用户问题】\n{query}")
            parts.append("\n请根据以上文档内容回答用户问题。")

            return "\n".join(parts)


class ContextWindowManager:
    """上下文窗口管理器（防止超出模型限制）"""

    def __init__(self, max_tokens: int = 8192):
        """
        初始化

        Args:
            max_tokens: 模型的最大上下文窗口
        """
        self.max_tokens = max_tokens
        self.reserved_for_response = 2048  # 为模型响应预留的token数
        self.available_for_input = max_tokens - self.reserved_for_response

    def fits_in_window(self, prompt: str) -> bool:
        """检查提示词是否适合上下文窗口"""
        estimated_tokens = len(prompt) // 2  # 粗略估算
        return estimated_tokens <= self.available_for_input

    def truncate_if_needed(
        self,
        prompt: str,
        strategy: str = "recent"
    ) -> str:
        """
        如果超出窗口，截断提示词

        Args:
            prompt: 原始提示词
            strategy: 截断策略 ("recent", "head_tail")

        Returns:
            截断后的提示词
        """
        estimated_tokens = len(prompt) // 2

        if estimated_tokens <= self.available_for_input:
            return prompt

        # 需要截断
        target_length = int(self.available_for_input * 1.5)  # 转换为字符数

        if strategy == "recent":
            # 保留最近的部分
            return prompt[-target_length:]
        elif strategy == "head_tail":
            # 保留头部和尾部
            half_length = target_length // 2
            return f"{prompt[:half_length]}\n...[中间省略]...\n{prompt[-half_length:]}"
        else:
            return prompt[:target_length]


# 全局单例
_context_manager_instance: Optional[ContextManager] = None


def get_context_manager(
    max_history_turns: int = 5,
    max_history_tokens: int = 2000,
    max_context_tokens: int = 4000
) -> ContextManager:
    """获取上下文管理器实例"""
    global _context_manager_instance
    if _context_manager_instance is None:
        _context_manager_instance = ContextManager(
            max_history_turns=max_history_turns,
            max_history_tokens=max_history_tokens,
            max_context_tokens=max_context_tokens
        )
    return _context_manager_instance

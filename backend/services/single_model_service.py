"""
SingleModelService - 单模型服务（Ollama直接API版本）

通过 Ollama HTTP API 直接调用 DeepSeek-R1-Distill-Qwen-32B 模型
无需 LangChain，更快的响应速度
"""

import logging
import time
import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """生成配置"""
    temperature: float = 0.2
    num_predict: int = 2048
    top_p: float = 0.9
    top_k: int = 20


class SingleModelService:
    """
    单模型服务（Ollama直接API版本）

    直接使用 HTTP API 调用，无需 LangChain 中间层
    """

    def __init__(
        self,
        base_url: str = None,
        model_name: str = None,
        generation_config: GenerationConfig = None
    ):
        """
        初始化单模型服务

        Args:
            base_url: Ollama 服务地址
            model_name: 模型名称
            generation_config: 生成配置
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model_name = model_name or os.getenv("LLM_MODEL_14B", "qwen2.5:32b")
        self.generation_config = generation_config or GenerationConfig()

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_time": 0.0,
            "avg_time_per_request": 0.0
        }

        logger.info(f"SingleModelService: {self.base_url}, model={self.model_name}")

    def is_ready(self) -> bool:
        """检查服务是否就绪"""
        try:
            import requests
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except:
            return False

    def chat(
        self,
        message: str,
        context: List[str] = None,
        chat_history: List[Dict[str, str]] = None,
        system_prompt: str = None,
        generation_config: GenerationConfig = None
    ) -> Dict[str, Any]:
        """
        聊天接口

        Args:
            message: 用户消息
            context: 检索到的文档上下文
            chat_history: 对话历史
            system_prompt: 系统提示词
            generation_config: 生成配置

        Returns:
            响应字典
        """
        start_time = time.time()

        try:
            import requests

            # 构建提示词
            prompt = self._build_prompt(message, context, chat_history, system_prompt)

            # 调用 Ollama API
            config = generation_config or self.generation_config

            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": config.temperature,
                    "num_predict": config.num_predict,
                    "top_p": config.top_p,
                    "top_k": config.top_k
                }
            }

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=300  # 增加到5分钟
            )
            response.raise_for_status()

            data = response.json()
            answer_text = data.get("response", "")

            # 清理响应
            answer_text = self._clean_response(answer_text)

            duration = time.time() - start_time

            # 更新统计
            self.stats["total_requests"] += 1
            self.stats["total_time"] += duration
            self.stats["avg_time_per_request"] = (
                self.stats["total_time"] / self.stats["total_requests"]
            )

            logger.info(f"Response completed: time={duration:.2f}s")

            return {
                "success": True,
                "answer": answer_text,
                "model_used": "32b",
                "model_name": self.model_name,
                "processing_time": round(duration, 2),
                "tokens_used": data.get("eval_count", 0)
            }

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": f"抱歉，处理您的消息时出现错误：{str(e)}"
            }

    def _build_prompt(
        self,
        message: str,
        context: List[str] = None,
        chat_history: List[Dict[str, str]] = None,
        system_prompt: str = None
    ) -> str:
        """构建提示词"""
        parts = []

        # 系统提示词
        if system_prompt:
            parts.append(system_prompt)
        else:
            formatted_context = self._format_context(context)
            parts.append(f"""你是一个电信渠道政策助手，专门帮助渠道店员查询和理解电信业务政策。

【重要原则】
1. 仅基于提供的文档内容回答，不要编造或猜测答案
2. 如果文档中没有明确的答案，直接告知用户"文档中没有找到相关信息"
3. 回答要专业、清晰，避免冗冗

【检索到的文档片段】
{formatted_context}

请根据以上文档内容回答用户的问题。""")

        # 对话历史
        if chat_history:
            for msg in chat_history[-5:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    parts.append(f"\n用户: {content}")
                elif role == "assistant":
                    parts.append(f"\n助手: {content}")

        # 当前问题
        parts.append(f"\n用户: {message}")
        parts.append("\n助手:")

        return "\n".join(parts)

    def _clean_response(self, text: str) -> str:
        """清理响应文本"""
        text = text.strip()

        # 移除可能的特殊标记
        if "<|im_end|>" in text:
            text = text.split("<|im_end|>")[0].strip()

        if "\n用户:" in text:
            text = text.split("\n用户:")[0].strip()

        return text

    def _format_context(self, contexts: List[str]) -> str:
        """格式化检索上下文"""
        if not contexts:
            return "（未检索到相关文档）"

        formatted = []
        for i, ctx in enumerate(contexts[:3], 1):
            snippet = ctx[:1500] if len(ctx) > 1500 else ctx
            formatted.append(f"[文档片段 {i}]\n{snippet}\n")

        return "\n".join(formatted)

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy" if self.is_ready() else "disconnected",
            "base_url": self.base_url,
            "model_name": self.model_name,
            "statistics": self.stats
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()


# 全局单例
_single_model_service: Optional[SingleModelService] = None


def get_single_model_service(
    base_url: str = None,
    model_name: str = None,
    generation_config: GenerationConfig = None
) -> SingleModelService:
    """获取单模型服务实例（单例模式）"""
    global _single_model_service
    if _single_model_service is None:
        _single_model_service = SingleModelService(
            base_url=base_url,
            model_name=model_name,
            generation_config=generation_config
        )
    return _single_model_service


def set_single_model_service(service: SingleModelService):
    """设置单模型服务实例"""
    global _single_model_service
    _single_model_service = service

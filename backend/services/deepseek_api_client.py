"""
DeepSeek API 客户端
使用 DeepSeek 官方 API 替代本地推理
"""

import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DeepSeekAPIClient:
    """DeepSeek API 客户端"""

    def __init__(
        self,
        api_key: str = None,
        api_url: str = "https://api.deepseek.com/v1/chat/completions",
        model: str = "deepseek-chat",
        timeout: float = 30.0,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY not set in environment variables")

        self.api_url = api_url
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens

        # 统计信息
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'total_latency': 0.0
        }

        logger.info(f"✅ DeepSeek API 客户端初始化完成")
        logger.info(f"   模型: {self.model}")
        logger.info(f"   超时: {self.timeout}s")
        logger.info(f"   温度: {self.temperature}")

    async def chat(
        self,
        message: str,
        context: List[str] = None,
        system_prompt: str = None,
        chat_history: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        发送聊天请求到 DeepSeek API

        Args:
            message: 用户消息
            context: 上下文文档列表
            system_prompt: 系统提示词
            chat_history: 对话历史（支持多轮对话）

        Returns:
            响应结果
        """
        start_time = datetime.now()

        try:
            # 构建消息列表
            messages = []

            # 添加系统提示
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            # 添加上下文
            if context:
                # 只使用前 3 个最相关的上下文
                for i, ctx in enumerate(context[:3]):
                    messages.append({
                        "role": "system",
                        "content": f"参考文档 {i+1}：{ctx}"
                    })

            # 添加对话历史（支持多轮对话）
            if chat_history:
                for hist_msg in chat_history:
                    role = hist_msg.get("role", "user")
                    # 映射角色名称
                    if role == "user":
                        api_role = "user"
                    elif role == "assistant":
                        api_role = "assistant"
                    else:
                        continue  # 跳过其他角色

                    messages.append({
                        "role": api_role,
                        "content": hist_msg.get("content", "")
                    })

            # 添加当前用户消息
            messages.append({
                "role": "user",
                "content": message
            })

            # 发送请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                        "stream": False
                    }
                )

                response.raise_for_status()
                result = response.json()

            # 提取响应内容
            content = result["choices"][0]["message"]["content"]

            # 提取 token 使用情况
            usage = result.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)

            # 计算延迟
            latency = (datetime.now() - start_time).total_seconds()

            # 更新统计
            self.stats['total_requests'] += 1
            self.stats['successful_requests'] += 1
            self.stats['total_tokens'] += total_tokens
            self.stats['total_latency'] += latency

            logger.info(f"✅ API 调用成功: {latency:.2f}s, {total_tokens} tokens")

            return {
                "success": True,
                "content": content,
                "model": self.model,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens
                },
                "latency": latency,
                "timestamp": datetime.now().isoformat()
            }

        except httpx.TimeoutException as e:
            logger.error(f"❌ API 超时: {e}")
            self.stats['total_requests'] += 1
            self.stats['failed_requests'] += 1
            return {
                "success": False,
                "error": "API 请求超时",
                "content": None
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"❌ API 错误: {e.response.status_code} - {e.response.text}")
            self.stats['total_requests'] += 1
            self.stats['failed_requests'] += 1
            return {
                "success": False,
                "error": f"API 返回错误: {e.response.status_code}",
                "content": None
            }

        except Exception as e:
            logger.error(f"❌ API 调用失败: {e}")
            self.stats['total_requests'] += 1
            self.stats['failed_requests'] += 1
            return {
                "success": False,
                "error": str(e),
                "content": None
            }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        avg_latency = 0.0
        if self.stats['successful_requests'] > 0:
            avg_latency = self.stats['total_latency'] / self.stats['successful_requests']

        return {
            **self.stats,
            'success_rate': self.stats['successful_requests'] / max(self.stats['total_requests'], 1),
            'avg_latency': avg_latency,
            'avg_tokens_per_request': self.stats['total_tokens'] / max(self.stats['successful_requests'], 1)
        }

    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'total_latency': 0.0
        }
        logger.info("📊 统计信息已重置")


# 全局实例
_deepseek_api_client = None

def get_deepseek_api_client() -> DeepSeekAPIClient:
    """获取 DeepSeek API 客户端实例（单例模式）"""
    global _deepseek_api_client
    if _deepseek_api_client is None:
        _deepseek_api_client = DeepSeekAPIClient()
    return _deepseek_api_client

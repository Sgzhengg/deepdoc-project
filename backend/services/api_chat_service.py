"""
API 聊天服务 - 使用 DeepSeek API
替代本地推理模型
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from services.deepseek_api_client import DeepSeekAPIClient

logger = logging.getLogger(__name__)


class APIChatService:
    """
    基于 DeepSeek API 的聊天服务

    替代本地 Ollama 推理，提供更快的响应速度
    """

    def __init__(
        self,
        model: str = "deepseek-chat",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        timeout: float = 30.0
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

        # 初始化 API 客户端
        try:
            self.api_client = DeepSeekAPIClient(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
            logger.info("✅ API 聊天服务初始化完成")
        except Exception as e:
            logger.error(f"❌ API 聊天服务初始化失败: {e}")
            raise

    async def chat(
        self,
        message: str,
        chat_history: List[Dict] = None,
        context: List[str] = None,
        config: Dict = None
    ) -> Dict[str, Any]:
        """
        处理聊天请求

        Args:
            message: 用户消息
            chat_history: 聊天历史
            context: 文档上下文
            config: 额外配置

        Returns:
            响应结果
        """
        start_time = datetime.now()

        try:
            # 构建系统提示
            system_prompt = self._build_system_prompt(context)

            # 调用 API（传递对话历史以支持多轮对话）
            result = await self.api_client.chat(
                message=message,
                context=context or [],
                system_prompt=system_prompt,
                chat_history=chat_history or []  # 传递历史消息
            )

            if not result["success"]:
                return {
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                    "answer": "抱歉，AI 服务暂时不可用，请稍后重试。"
                }

            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds()

            # 构建响应
            return {
                "success": True,
                "answer": result["content"],
                "model": self.model,
                "model_used": self.model,  # 添加此字段
                "model_name": self.model,  # 添加此字段
                "complexity": {"score": 0.5, "intent": "qa"},  # 添加此字段
                "model_stats": {
                    "model_used": self.model,
                    "model_name": self.model,
                    "processing_time": processing_time,
                    "tokens_used": result["usage"]["total_tokens"],
                    "latency": result["latency"],
                    "source": "api"
                },
                "reasoning": ["使用 DeepSeek API"],
                "sources": context or [],
                "confidence": 0.95
            }

        except Exception as e:
            logger.error(f"❌ 聊天处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": "抱歉，处理请求时出现错误，请稍后重试。"
            }

    def _build_system_prompt(self, context: List[str] = None) -> str:
        """构建系统提示词"""
        prompt = """你是一个专业的文档查询助手，负责基于提供的参考文档回答用户问题。

## ⚠️ 最重要原则
**当参考文档中没有用户问题的相关信息时，必须明确回答："知识库中无此相关内容"，绝对不能编造、猜测或推断任何文档外的信息！**

## 核心原则
1. **严格基于文档**：只能使用参考文档中明确提到的信息
2. **无信息时明确拒绝**：如果文档中没有答案，必须说"知识库中无此相关内容"
3. **准确性优先**：保留原始数字、单位、金额，不要估算或省略
4. **完整提取**：从文档片段中提取所有相关信息，注意表格和列表数据可能分散在不同片段中

## 多轮对话能力
你处于一个多轮对话环境中，需要：
1. **理解上下文**：记住之前的问题和回答，理解追问与之前问题的关联
2. **指代消解**：理解"它"、"这个"、"那个"等指代词，关联到之前提到的具体内容
3. **信息累积**：在多轮对话中逐步累积信息，构建完整的答案
4. **对比分析**：当用户要求对比时，基于之前的对话内容进行对比

## 回答要求
1. **信息提取**：
   - 准确提取所有数字、单位、日期、金额等量化信息
   - 区分不同类别或类型的信息（如"通用/定向"、"套内/套外"等分类）
   - 识别并列出限制条件、注意事项、特殊说明

2. **结构化呈现**：
   - 使用项目符号（•）或编号列出多项内容
   - 相关信息归类展示
   - 使用清晰的层次结构

3. **追问响应**：
   - 如果用户追问，先回顾之前提到的相关内容
   - 在此基础上补充新信息
   - 明确指出这是对之前哪个内容的补充或对比

4. **无信息处理**：
   - **关键**：如果参考文档完全没有相关内容，必须回答："抱歉，知识库中无此相关内容"
   - **关键**：如果文档中只有部分相关信息，回答已知部分，并明确说明"文档中未提及XXX部分"
   - **关键**：绝不使用"可能"、"大概"、"一般来说"等模糊词汇来掩盖信息缺失
   - **关键**：绝不根据常识或外部知识补充文档中没有的信息

## 回答格式
- 先给出简洁的直接回答（1-2句话）
- 如果是追问，先简要回顾上下文
- 然后分段详细说明，使用列表呈现具体内容
- 最后标注信息来源文档名称
- **如果文档无相关信息**：只回答"知识库中无此相关内容"，不要添加任何其他内容
"""

        if context:
            prompt += f"\n\n## 参考文档\n已提供 {len(context)} 个参考文档片段。请注意：\n"
            prompt += "- ⚠️ 只能基于这些文档片段回答问题\n"
            prompt += "- 文档片段可能不完整，表格和列表数据可能分散在不同片段中\n"
            prompt += "- 需要综合理解多个片段，提取完整信息\n"
            prompt += '- **如果这些文档片段中没有用户问题的答案，必须说"知识库中无此相关内容"**\n'
            prompt += "- 如果片段中信息相互矛盾或缺失，基于最完整的片段回答并说明"
        else:
            # 没有提供参考文档时
            prompt += '\n\n⚠️ **注意：当前没有提供任何参考文档**。如果用户提出问题，请回答"知识库中无此相关内容"。'

        return prompt

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            stats = self.api_client.get_stats()
            return {
                "status": "healthy",
                "model": self.model,
                "stats": stats,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }


# 全局实例
_api_chat_service = None

def get_api_chat_service() -> APIChatService:
    """获取 API 聊天服务实例（单例模式）"""
    global _api_chat_service
    if _api_chat_service is None:
        _api_chat_service = APIChatService()
    return _api_chat_service

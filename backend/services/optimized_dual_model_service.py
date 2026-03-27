"""
优化的双模型聊天服务

整合查询路由、上下文管理、提示词模板等优化组件
"""

import logging
import time
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from langchain_ollama import ChatOllama

from query_router import EnhancedQueryRouter, get_query_router, QueryType
from context_manager import ContextManager, get_context_manager
from prompts import (
    SimpleQueryPrompt,
    ComplexQueryPrompt,
    FollowUpPrompt,
    CalculationPromptTemplate,
    prompt_builder,
    PromptBuilder
)
from ollama_wrapper import get_model_invoker

logger = logging.getLogger(__name__)


@dataclass
class ChatResponse:
    """聊天响应"""
    success: bool
    answer: str
    model_used: str
    query_type: str
    complexity_score: float
    processing_time: float
    tokens_used: int = 0
    reasoning: List[str] = None
    sources: List[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "answer": self.answer,
            "model_used": self.model_used,
            "query_type": self.query_type,
            "complexity_score": self.complexity_score,
            "processing_time": self.processing_time,
            "tokens_used": self.tokens_used,
            "reasoning": self.reasoning or [],
            "sources": self.sources or [],
            "error": self.error
        }


class OptimizedDualModelService:
    """
    优化的双模型聊天服务

    核心优化：
    1. 智能查询路由（动态选择7B/14B）
    2. 增强的上下文管理
    3. 针对性的提示词模板
    4. 更低的复杂度阈值（更多问题使用14B）
    """

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        model_7b: str = "qwen2.5:7b",
        model_14b: str = "qwen2.5:14b",
        complexity_threshold: float = 5.0,
        max_history_turns: int = 5
    ):
        """
        初始化优化的双模型服务

        Args:
            ollama_base_url: Ollama服务地址
            model_7b: 7B模型名称
            model_14b: 14B模型名称
            complexity_threshold: 复杂度阈值（降低以更多使用14B）
            max_history_turns: 最大历史轮数
        """
        self.ollama_base_url = ollama_base_url
        self.model_7b = model_7b
        self.model_14b = model_14b
        self.complexity_threshold = complexity_threshold

        # 初始化组件
        self.router = get_query_router(threshold=complexity_threshold)
        self.context_manager = get_context_manager(
            max_history_turns=max_history_turns
        )

        # 初始化提示词模板
        self._init_prompt_templates()

        # 初始化模型（延迟加载）
        self.llm_7b: Optional[ChatOllama] = None
        self.llm_14b: Optional[ChatOllama] = None

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "7b_count": 0,
            "14b_count": 0,
            "follow_up_count": 0,
            "avg_complexity": 0.0,
            "avg_processing_time": 0.0
        }

        logger.info(
            f"OptimizedDualModelService initialized: "
            f"7B={model_7b}, 14B={model_14b}, threshold={complexity_threshold}"
        )

    def _init_prompt_templates(self):
        """初始化提示词模板"""
        # 注册简单查询模板
        prompt_builder.register_template(
            "simple",
            SimpleQueryPrompt()
        )

        # 注册复杂查询模板
        prompt_builder.register_template(
            "complex",
            ComplexQueryPrompt()
        )

        # 注册追问模板
        prompt_builder.register_template(
            "follow_up",
            FollowUpPrompt()
        )

        # 注册计算模板
        prompt_builder.register_template(
            "calculation",
            CalculationPromptTemplate()
        )

        # 注册对比模板
        prompt_builder.register_template(
            "comparison",
            ComplexQueryPrompt()  # 暂时使用复杂查询模板
        )

        # 注册条件判断模板
        prompt_builder.register_template(
            "conditional",
            ComplexQueryPrompt()  # 暂时使用复杂查询模板
        )

        logger.info("Prompt templates initialized")

    def initialize(
        self,
        vector_storage=None,
        embedding_service=None
    ):
        """
        初始化服务（加载模型）

        Args:
            vector_storage: 向量存储（可选）
            embedding_service: 嵌入服务（可选）
        """
        logger.info("Initializing OptimizedDualModelService...")

        try:
            # 初始化7B模型
            logger.info(f"Loading 7B model: {self.model_7b}")
            self.llm_7b = ChatOllama(
                base_url=self.ollama_base_url,
                model=self.model_7b,
                temperature=0.2,
                num_predict=1000,
                top_k=20,
                top_p=0.9,
                timeout=60
            )
            logger.info("✅ 7B model loaded")

            # 初始化14B模型
            logger.info(f"Loading 14B model: {self.model_14b}")
            self.llm_14b = ChatOllama(
                base_url=self.ollama_base_url,
                model=self.model_14b,
                temperature=0.2,  # 降低温度以提高准确性
                num_predict=2000,  # 允许更长输出
                top_k=20,
                top_p=0.9,
                timeout=90  # 更长的超时时间
            )
            logger.info("✅ 14B model loaded")

            self.vector_storage = vector_storage
            self.embedding_service = embedding_service

            logger.info("✅ OptimizedDualModelService initialization complete")
            return True

        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False

    def chat(
        self,
        message: str,
        context: List[str] = None,
        chat_history: List[Dict[str, str]] = None,
        session_id: str = None
    ) -> ChatResponse:
        """
        处理聊天请求（同步版本）

        Args:
            message: 用户消息
            context: 检索到的文档上下文
            chat_history: 对话历史
            session_id: 会话ID（用于统计）

        Returns:
            ChatResponse: 聊天响应
        """
        start_time = time.time()

        try:
            # 1. 路由查询
            route_decision = self.router.route(message, chat_history)

            # 2. 准备上下文
            processed_history, processed_context = self.context_manager.prepare_context(
                query=message,
                chat_history=chat_history or [],
                retrieval_results=[{"text": ctx, "score": 0.8} for ctx in (context or [])],
                is_follow_up=route_decision.is_follow_up
            )

            # 3. 选择模型
            if route_decision.model_size.value == "14b":
                llm = self.llm_14b
                model_name = self.model_14b
                self.stats["14b_count"] += 1
            else:
                llm = self.llm_7b
                model_name = self.model_7b
                self.stats["7b_count"] += 1

            # 4. 获取提示词模板
            prompt_template = prompt_builder.get_template(route_decision.prompt_template)

            # 5. 构建完整提示词
            full_prompt = prompt_template.build_prompt(
                query=message,
                context=processed_context,
                chat_history=processed_history
            )

            # 6. 调用模型
            logger.info(f"Using {model_name} for query (type={route_decision.query_type.value})")

            # 使用 Ollama CLI 调用模型
            response_text = self._call_model_by_name(model_name, full_prompt)

            # 7. 后处理
            response_text = self._post_process(response_text)

            # 8. 更新统计
            processing_time = time.time() - start_time
            self.stats["total_requests"] += 1
            if route_decision.is_follow_up:
                self.stats["follow_up_count"] += 1

            # 更新平均复杂度
            total = self.stats["total_requests"]
            self.stats["avg_complexity"] = (
                (self.stats["avg_complexity"] * (total - 1) + route_decision.complexity_score) / total
            )
            self.stats["avg_processing_time"] = (
                (self.stats["avg_processing_time"] * (total - 1) + processing_time) / total
            )

            # 9. 构建响应
            response = ChatResponse(
                success=True,
                answer=response_text,
                model_used=model_name,
                query_type=route_decision.query_type.value,
                complexity_score=route_decision.complexity_score,
                processing_time=round(processing_time, 2),
                reasoning=route_decision.reasons,
                sources=[{"type": "document"} for _ in (context or [])]
            )

            logger.info(
                f"Chat completed: model={model_name}, "
                f"time={processing_time:.2f}s, "
                f"complexity={route_decision.complexity_score:.1f}"
            )

            return response

        except Exception as e:
            logger.error(f"Chat failed: {e}")
            processing_time = time.time() - start_time

            return ChatResponse(
                success=False,
                answer=f"抱歉，处理您的消息时出现错误：{str(e)}",
                model_used="unknown",
                query_type="error",
                complexity_score=0.0,
                processing_time=round(processing_time, 2),
                error=str(e)
            )

    def _call_model_by_name(self, model_name: str, prompt: str) -> str:
        """通过模型名称调用（使用 Ollama CLI）"""
        try:
            # 使用模型调用器
            invoker = get_model_invoker()
            response = invoker.invoke(model_name, prompt)

            return response

        except Exception as e:
            logger.error(f"Model invocation failed: {e}")
            raise

    def _call_model(self, llm: ChatOllama, prompt: str) -> str:
        """调用模型（保留用于兼容性，但已弃用）"""
        # 获取模型名称并调用新方法
        model_name = getattr(llm, 'model', 'qwen2.5:7b')
        return self._call_model_by_name(model_name, prompt)

    def _post_process(self, text: str) -> str:
        """后处理模型输出"""
        # 清理特殊标记
        text = text.strip()

        # 移除可能的思考标记
        if "<|思考|>" in text:
            text = text.split("<|思考|>")[0].strip()

        # 移除结束标记
        if "<|im_end|>" in text:
            text = text.split("<|im_end|>")[0].strip()

        return text

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy" if (self.llm_7b and self.llm_14b) else "uninitialized",
            "model_7b": self.model_7b,
            "model_14b": self.model_14b,
            "complexity_threshold": self.complexity_threshold,
            "statistics": self.stats
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "14b_ratio": round(
                self.stats["14b_count"] / max(self.stats["total_requests"], 1) * 100,
                1
            ) if self.stats["total_requests"] > 0 else 0,
            "follow_up_ratio": round(
                self.stats["follow_up_count"] / max(self.stats["total_requests"], 1) * 100,
                1
            ) if self.stats["total_requests"] > 0 else 0
        }


# 全局单例
_service_instance: Optional[OptimizedDualModelService] = None


def get_optimized_service(
    ollama_base_url: str = "http://localhost:11434",
    model_7b: str = "qwen2.5:7b",
    model_14b: str = "qwen2.5:14b",
    complexity_threshold: float = 5.0
) -> OptimizedDualModelService:
    """获取优化的双模型服务实例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = OptimizedDualModelService(
            ollama_base_url=ollama_base_url,
            model_7b=model_7b,
            model_14b=model_14b,
            complexity_threshold=complexity_threshold
        )
    return _service_instance


def set_optimized_service(service: OptimizedDualModelService):
    """设置优化的双模型服务实例"""
    global _service_instance
    _service_instance = service

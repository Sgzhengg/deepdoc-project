"""
DualModelChatService - 双模型路由服务

根据查询复杂度自动选择使用 7B 或 14B 模型：
- 简单查询 → 7B 模型（快速响应）
- 复杂查询 → 14B 模型（更准确的分析和计算）

用户也可以手动指定使用哪个模型。
"""

import logging
import time
from typing import Dict, Any, Optional, List
from langchain_ollama import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel

from .complexity_analyzer import (
    QueryComplexityAnalyzer,
    get_complexity_analyzer,
    ComplexityResult,
    QueryIntent
)

logger = logging.getLogger(__name__)


class DualModelChatService:
    """
    双模型路由服务

    管理两个 LLM 实例，根据查询复杂度自动路由
    """

    def __init__(self):
        """初始化双模型聊天服务"""
        self.llm_7b: Optional[ChatOllama] = None
        self.llm_14b: Optional[ChatOllama] = None

        self.master_graph_7b = None
        self.master_graph_14b = None

        self.hybrid_retriever = None
        self.table_analyzer = None

        self.complexity_analyzer: Optional[QueryComplexityAnalyzer] = None

        # 模型配置
        self.model_name_7b: Optional[str] = None
        self.model_name_14b: Optional[str] = None
        self.threshold: float = 0.6

        # 统计信息
        self.stats = {
            "7b_count": 0,
            "14b_count": 0,
            "total_count": 0,
            "avg_complexity": 0.0,
            "model_switches": 0
        }

        self._initialized = False

    def initialize(
        self,
        ollama_base_url: str = "http://localhost:11434",
        model_name_7b: str = "qwen2.5:7b",
        model_name_14b: str = "qwen2.5:32b",
        threshold: float = 0.6,
        hybrid_retriever=None,
        table_analyzer=None,
        enable_14b: bool = True
    ):
        """
        初始化双模型服务

        Args:
            ollama_base_url: Ollama 服务地址
            model_name_7b: 7B 模型名称
            model_name_14b: 14B 模型名称
            threshold: 复杂度阈值，超过此值使用 14B
            hybrid_retriever: 混合检索器
            table_analyzer: 表格分析器
            enable_14b: 是否启用 14B 模型
        """
        try:
            logger.info("🔧 初始化 DualModelChatService...")

            self.model_name_7b = model_name_7b
            self.model_name_14b = model_name_14b
            self.threshold = threshold
            self.hybrid_retriever = hybrid_retriever
            self.table_analyzer = table_analyzer

            # 初始化复杂度分析器
            self.complexity_analyzer = QueryComplexityAnalyzer(threshold=threshold)

            # 初始化 7B 模型
            logger.info(f"📦 初始化 7B 模型: {model_name_7b}")
            self.llm_7b = ChatOllama(
                base_url=ollama_base_url,
                model=model_name_7b,
                temperature=0.2,
                num_predict=1000,
                top_k=20,
                top_p=0.9,
                timeout=60  # 超时时间60秒
            )
            logger.info(f"✅ 7B 模型初始化完成")

            # 初始化 14B 模型（如果启用）
            if enable_14b:
                logger.info(f"📦 初始化大模型: {model_name_14b}")
                try:
                    # 根据模型名称判断是否是 32B 模型，使用不同的参数
                    is_32b_model = "32b" in model_name_14b.lower() or "deepseek-r1" in model_name_14b.lower()

                    if is_32b_model:
                        # 32B 模型参数：更精确、更长输出、更长超时
                        self.llm_14b = ChatOllama(
                            base_url=ollama_base_url,
                            model=model_name_14b,
                            temperature=0.1,  # 降低温度以获得更准确的答案
                            num_predict=3000,  # 允许更长输出
                            top_k=20,
                            top_p=0.9,
                            timeout=120  # 32B 模型需要更长的超时时间
                        )
                        logger.info(f"✅ 大模型(32B)初始化完成 - 参数: temperature=0.1, num_predict=3000, timeout=120")
                    else:
                        # 14B 模型参数
                        self.llm_14b = ChatOllama(
                            base_url=ollama_base_url,
                            model=model_name_14b,
                            temperature=0.2,
                            num_predict=2000,
                            top_k=20,
                            top_p=0.9,
                            timeout=60
                        )
                        logger.info(f"✅ 大模型(14B)初始化完成")
                except Exception as e:
                    logger.warning(f"⚠️ 14B 模型初始化失败: {e}")
                    logger.info("📌 将仅使用 7B 模型")
                    self.llm_14b = None
            else:
                self.llm_14b = None
                logger.info("📌 14B 模型已禁用")

            # 初始化检索器
            if self.hybrid_retriever is None:
                try:
                    from vector_storage import VectorStorage
                    from embedding_service import EmbeddingService
                    import service_instance

                    vector_storage = VectorStorage()
                    if not vector_storage.connect():
                        raise Exception("向量存储连接失败")

                    embedding_service = EmbeddingService()
                    if not embedding_service.load_model():
                        raise Exception("嵌入模型加载失败")

                    # 设置到全局服务实例，供 document_routes.py 使用
                    service_instance.set_vector_storage(vector_storage)
                    service_instance.set_embedding_service(embedding_service)
                    logger.info("✅ 向量存储和嵌入服务已注册到全局实例")

                    from hybrid_search import HybridRetriever
                    self.hybrid_retriever = HybridRetriever(
                        embedding_service=embedding_service,
                        vector_storage=vector_storage
                    )
                    logger.info("✅ 混合检索器初始化完成")
                except Exception as e:
                    logger.error(f"❌ 混合检索器初始化失败: {e}")
                    logger.error(f"详细错误: {type(e).__name__}: {str(e)}")
                    import traceback
                    logger.error(f"堆栈跟踪:\n{traceback.format_exc()}")
                    # 关键：不要继续初始化，因为文档上传功能需要这些服务
                    raise Exception(f"向量检索服务初始化失败，文档上传功能将不可用: {e}")

            # 初始化表格分析器
            if self.table_analyzer is None:
                try:
                    from agents.enhanced_table_analyzer import get_table_analyzer
                    self.table_analyzer = get_table_analyzer()
                    logger.info("✅ 表格分析器初始化完成")
                except Exception as e:
                    logger.warning(f"⚠️ 表格分析器初始化失败: {e}")

            # 创建 MasterGraph 实例
            from langgraph_agents.master_graph import create_master_graph

            self.master_graph_7b = create_master_graph(
                llm=self.llm_7b,
                hybrid_retriever=self.hybrid_retriever,
                table_analyzer=self.table_analyzer,
                use_checkpointer=False
            )

            if self.llm_14b is not None:
                self.master_graph_14b = create_master_graph(
                    llm=self.llm_14b,
                    hybrid_retriever=self.hybrid_retriever,
                    table_analyzer=self.table_analyzer,
                    use_checkpointer=False
                )

            self._initialized = True
            logger.info("✅ DualModelChatService 初始化完成")
            logger.info(f"📊 配置: 7B={model_name_7b}, 14B={model_name_14b}, threshold={threshold}")

        except Exception as e:
            logger.error(f"❌ DualModelChatService 初始化失败: {e}")
            raise

    async def achat(
        self,
        message: str,
        session_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        config: Optional[Dict[str, Any]] = None,
        force_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        异步聊天

        Args:
            message: 用户消息
            session_id: 会话ID
            chat_history: 对话历史
            config: 额外配置
            force_model: 强制指定模型 ("7b" 或 "14b")

        Returns:
            响应字典，包含使用的模型信息
        """
        if not self._initialized:
            return {
                "success": False,
                "error": "DualModelChatService 未初始化",
                "answer": "抱歉，服务尚未初始化。"
            }

        start_time = time.time()

        try:
            # 分析查询复杂度（传入对话历史以更好地检测追问）
            complexity: ComplexityResult = self.complexity_analyzer.analyze(message, chat_history)

            # 决定使用哪个模型
            selected_model = self._select_model(complexity, force_model)
            use_14b = (selected_model == "14b")

            # 更新统计
            self.stats["total_count"] += 1
            if use_14b:
                self.stats["14b_count"] += 1
            else:
                self.stats["7b_count"] += 1

            # 更新平均复杂度
            total = self.stats["total_count"]
            self.stats["avg_complexity"] = (
                (self.stats["avg_complexity"] * (total - 1) + complexity.score) / total
            )

            logger.info(
                f"🎯 模型选择: {'14B' if use_14b else '7B'} | "
                f"复杂度={complexity.score:.2f} | "
                f"意图={complexity.intent.value}"
            )

            # 选择对应的 graph
            graph = self.master_graph_14b if use_14b else self.master_graph_7b

            # 调用处理
            result = await graph.aprocess(
                user_query=message,
                session_id=session_id,
                chat_history=chat_history,
                config=config
            )

            # 计算处理时间
            processing_time = time.time() - start_time

            # 添加模型信息到响应
            result["model_used"] = "14b" if use_14b else "7b"
            result["model_name"] = self.model_name_14b if use_14b else self.model_name_7b
            result["complexity"] = {
                "score": complexity.score,
                "intent": complexity.intent.value,
                "confidence": complexity.confidence,
                "reasons": complexity.reasons
            }
            result["processing_time"] = round(processing_time, 2)

            logger.info(
                f"✅ 响应完成: model={result['model_used']}, "
                f"time={processing_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"❌ 聊天处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": "抱歉，处理您的消息时出现错误。"
            }

    def chat(
        self,
        message: str,
        session_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        config: Optional[Dict[str, Any]] = None,
        force_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步聊天

        Args:
            message: 用户消息
            session_id: 会话ID
            chat_history: 对话历史
            config: 额外配置
            force_model: 强制指定模型 ("7b" 或 "14b")

        Returns:
            响应字典
        """
        if not self._initialized:
            return {
                "success": False,
                "error": "DualModelChatService 未初始化",
                "answer": "抱歉，服务尚未初始化。"
            }

        start_time = time.time()

        try:
            # 分析查询复杂度（传入对话历史以更好地检测追问）
            complexity: ComplexityResult = self.complexity_analyzer.analyze(message, chat_history)

            # 决定使用哪个模型
            selected_model = self._select_model(complexity, force_model)
            use_14b = (selected_model == "14b")

            # 更新统计
            self.stats["total_count"] += 1
            if use_14b:
                self.stats["14b_count"] += 1
            else:
                self.stats["7b_count"] += 1

            # 更新平均复杂度
            total = self.stats["total_count"]
            self.stats["avg_complexity"] = (
                (self.stats["avg_complexity"] * (total - 1) + complexity.score) / total
            )

            logger.info(
                f"🎯 模型选择: {'14B' if use_14b else '7B'} | "
                f"复杂度={complexity.score:.2f} | "
                f"意图={complexity.intent.value}"
            )

            # 选择对应的 graph
            graph = self.master_graph_14b if use_14b else self.master_graph_7b

            # 调用处理
            result = graph.process(
                user_query=message,
                session_id=session_id,
                chat_history=chat_history,
                config=config
            )

            # 计算处理时间
            processing_time = time.time() - start_time

            # 添加模型信息到响应
            result["model_used"] = "14b" if use_14b else "7b"
            result["model_name"] = self.model_name_14b if use_14b else self.model_name_7b
            result["complexity"] = {
                "score": complexity.score,
                "intent": complexity.intent.value,
                "confidence": complexity.confidence,
                "reasons": complexity.reasons
            }
            result["processing_time"] = round(processing_time, 2)

            logger.info(
                f"✅ 响应完成: model={result['model_used']}, "
                f"time={processing_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"❌ 聊天处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": "抱歉，处理您的消息时出现错误。"
            }

    def _select_model(
        self,
        complexity: ComplexityResult,
        force_model: Optional[str] = None
    ) -> str:
        """
        选择使用的模型

        Args:
            complexity: 复杂度分析结果
            force_model: 强制指定的模型

        Returns:
            "7b" 或 "14b"
        """
        # 如果强制指定，使用指定的模型
        if force_model:
            if force_model.lower() in ["7b", "14b"]:
                # 检查 14B 是否可用
                if force_model.lower() == "14b" and self.llm_14b is None:
                    logger.warning("⚠️ 请求使用 14B 但模型不可用，降级到 7B")
                    return "7b"
                return force_model.lower()

        # 如果 14B 不可用，使用 7B
        if self.llm_14b is None:
            return "7b"

        # 根据复杂度选择
        if complexity.use_large_model:
            return "14b"
        return "7b"

    def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            组件状态
        """
        status = {
            "initialized": self._initialized,
            "components": {}
        }

        if self._initialized:
            status["components"]["llm_7b"] = {
                "status": "healthy" if self.llm_7b else "not_configured",
                "model": self.model_name_7b
            }
            status["components"]["llm_14b"] = {
                "status": "healthy" if self.llm_14b else "not_configured",
                "model": self.model_name_14b
            }
            status["components"]["master_graph_7b"] = {
                "status": "healthy" if self.master_graph_7b else "not_configured"
            }
            status["components"]["master_graph_14b"] = {
                "status": "healthy" if self.master_graph_14b else "not_configured"
            }
            status["components"]["complexity_analyzer"] = {
                "status": "healthy",
                "threshold": self.threshold
            }
            status["statistics"] = self.stats

        return status

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取使用统计

        Returns:
            统计信息
        """
        return {
            "7b_count": self.stats["7b_count"],
            "14b_count": self.stats["14b_count"],
            "total_count": self.stats["total_count"],
            "avg_complexity": round(self.stats["avg_complexity"], 3),
            "14b_ratio": round(
                self.stats["14b_count"] / max(self.stats["total_count"], 1) * 100, 1
            ) if self.stats["total_count"] > 0 else 0
        }


# 全局单例
_dual_model_service: Optional[DualModelChatService] = None


def get_dual_model_service() -> DualModelChatService:
    """
    获取双模型服务实例（单例模式）

    Returns:
        DualModelChatService 实例
    """
    global _dual_model_service
    if _dual_model_service is None:
        _dual_model_service = DualModelChatService()
    return _dual_model_service


def set_dual_model_service(service: DualModelChatService):
    """
    设置双模型服务实例

    Args:
        service: DualModelChatService 实例
    """
    global _dual_model_service
    _dual_model_service = service

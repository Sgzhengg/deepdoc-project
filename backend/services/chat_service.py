"""
ChatService - 统一聊天服务
基于LangGraph的AI聊天服务
"""

import logging
from typing import Dict, Any, Optional, List
from langchain_ollama import ChatOllama

from hybrid_search import HybridRetriever
from agents.enhanced_table_analyzer import get_table_analyzer

logger = logging.getLogger(__name__)

# 导入 CLI Ollama 客户端（用于 Windows API 不兼容问题）
from services.cli_ollama import CLIChatOllama

# 性能优化：根据配置选择不同的MasterGraph实现
import os
optimization_mode = os.getenv("OPTIMIZATION_MODE", "original").lower()

if optimization_mode == "one_step":
    # 激进优化版：1步流程（推荐）
    from langgraph_agents.one_step_master_graph import OneStepMasterGraph
    logger.info("🚀 使用激进优化版MasterGraph (1步流程)")
    # 创建适配器工厂函数
    def create_master_graph(*args, **kwargs):
        # 移除不支持的参数
        kwargs.pop('use_checkpointer', None)
        return OneStepMasterGraph(*args, **kwargs)
elif optimization_mode == "two_step":
    # 保守优化版：2步流程
    from langgraph_agents.ultra_simple_master_graph import UltraSimpleMasterGraph
    logger.info("⚡ 使用保守优化版MasterGraph (2步流程)")
    def create_master_graph(*args, **kwargs):
        # 移除不支持的参数
        kwargs.pop('use_checkpointer', None)
        return UltraSimpleMasterGraph(*args, **kwargs)
else:
    # 原版：3步流程
    from langgraph_agents.master_graph import create_master_graph
    logger.info("📊 使用原版MasterGraph (3步流程)")


class ChatService:
    """
    统一聊天服务

    基于LangGraph多Agent系统处理所有AI交互
    """

    def __init__(self):
        """初始化聊天服务"""
        self.master_graph = None
        self.llm = None
        self.hybrid_retriever = None
        self.table_analyzer = None
        self._initialized = False

    def initialize(
        self,
        ollama_base_url: str = "http://localhost:11434",
        model_name: str = "qwen2.5:7b",
        hybrid_retriever=None,
        table_analyzer=None,
    ):
        """
        初始化聊天服务

        Args:
            ollama_base_url: Ollama服务地址
            model_name: 模型名称（使用Ollama API中的短名称）
            hybrid_retriever: 混合检索器
            table_analyzer: 表格分析器
        """
        # 检测是否在Docker环境中，使用Docker内部URL
        import os
        if os.path.exists('/.dockerenv'):
            # 获取ollama容器的IP地址
            ollama_ip = None
            try:
                # 解析容器名到IP映射
                with open('/etc/hosts', 'r') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#') and '8ca0279bac21' in line:
                            ollama_ip = line.split()[0]
                            break
            except Exception as e:
                logger.warning(f"无法读取 /etc/hosts: {e}")

            if ollama_ip:
                logger.info(f"检测到Ollama容器IP: {ollama_ip}")
                ollama_base_url = f"http://{ollama_ip}:11434"
                logger.info(f"使用Docker内部URL: {ollama_base_url}")
            else:
                logger.info(f"使用默认URL: {ollama_base_url}")

        try:
            logger.info("🔧 初始化ChatService...")

            # 检测是否需要使用 CLI 模式（Windows 上 deepseek 模型的 API 有 bug）
            use_cli = model_name.startswith("deepseek")

            if use_cli:
                logger.info("📌 使用 CLI 模式调用 Ollama (Windows API 兼容性问题)")
                self.llm = CLIChatOllama(
                    model_name=model_name,
                    temperature=0.2,
                    num_predict=1000,
                    timeout=300  # 增加到5分钟，应对长提示词
                )
                logger.info(f"✅ LLM初始化完成 (CLI模式): {model_name}")
            else:
                # 初始化LLM（优化参数以提高速度）
                self.llm = ChatOllama(
                    base_url=ollama_base_url,
                    model=model_name,
                    temperature=0.2,  # 降低temperature以获得更确定的输出
                    num_predict=1000,  # 限制最大生成长度以加快速度
                    top_k=20,  # 限制采样范围
                    top_p=0.9,  # nucleus sampling
                    timeout=60  # 超时时间60秒
                )
                logger.info(f"✅ LLM初始化完成: {model_name} (temperature=0.2, max_tokens=1000, timeout=60s)")

            # 初始化检索器
            if hybrid_retriever is None:
                try:
                    from vector_storage import VectorStorage
                    from embedding_service import EmbeddingService

                    vector_storage = VectorStorage()
                    vector_storage.connect()

                    embedding_service = EmbeddingService()
                    embedding_service.load_model()

                    hybrid_retriever = HybridRetriever(
                        embedding_service=embedding_service,
                        vector_storage=vector_storage
                    )
                    logger.info("✅ 混合检索器初始化完成")
                except Exception as e:
                    logger.warning(f"⚠️  混合检索器初始化失败: {e}")

            self.hybrid_retriever = hybrid_retriever

            # 初始化表格分析器
            if table_analyzer is None:
                try:
                    table_analyzer = get_table_analyzer()
                    logger.info("✅ 表格分析器初始化完成")
                except Exception as e:
                    logger.warning(f"⚠️  表格分析器初始化失败: {e}")

            self.table_analyzer = table_analyzer

            # 创建MasterGraph
            self.master_graph = create_master_graph(
                llm=self.llm,
                hybrid_retriever=self.hybrid_retriever,
                table_analyzer=self.table_analyzer,
                use_checkpointer=False  # 暂不使用检查点
            )

            self._initialized = True
            logger.info("✅ ChatService初始化完成")

        except Exception as e:
            logger.error(f"❌ ChatService初始化失败: {e}")
            raise

    async def achat(
        self,
        message: str,
        session_id: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        异步聊天

        Args:
            message: 用户消息
            session_id: 会话ID
            chat_history: 对话历史
            config: 额外配置

        Returns:
            响应字典
        """
        if not self._initialized:
            return {
                "success": False,
                "error": "ChatService未初始化",
                "answer": "抱歉，服务尚未初始化。"
            }

        try:
            # 调用MasterGraph处理
            result = await self.master_graph.aprocess(
                user_query=message,
                session_id=session_id,
                chat_history=chat_history,
                config=config
            )

            return result

        except Exception as e:
            logger.error(f"聊天处理失败: {e}")
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
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        同步聊天

        Args:
            message: 用户消息
            session_id: 会话ID
            chat_history: 对话历史
            config: 额外配置

        Returns:
            响应字典
        """
        if not self._initialized:
            return {
                "success": False,
                "error": "ChatService未初始化",
                "answer": "抱歉，服务尚未初始化。"
            }

        try:
            # 调用MasterGraph处理
            result = self.master_graph.process(
                user_query=message,
                session_id=session_id,
                chat_history=chat_history,
                config=config
            )

            return result

        except Exception as e:
            logger.error(f"聊天处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "answer": "抱歉，处理您的消息时出现错误。"
            }

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
            status["components"]["llm"] = {
                "status": "healthy" if self.llm else "not_configured"
            }
            status["components"]["master_graph"] = {
                "status": "healthy" if self.master_graph else "not_configured"
            }
            status["components"]["hybrid_retriever"] = {
                "status": "healthy" if self.hybrid_retriever else "not_configured"
            }
            status["components"]["table_analyzer"] = {
                "status": "healthy" if self.table_analyzer else "not_configured"
            }

        return status


# 全局单例
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """
    获取聊天服务实例（单例模式）

    Returns:
        ChatService实例
    """
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service

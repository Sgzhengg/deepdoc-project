"""
聊天路由 - 统一的AI聊天接口
支持双模型路由（7B/14B）
基于LangGraph多Agent系统
"""

import logging
import time
import asyncio
import sys
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# 导入后处理模块
from services.post_processor import AnswerPostProcessor
from services.concept_validator import ConceptValidator
from validation.integrity_checker import IntegrityChecker

# 初始化处理器（全局实例）
post_processor = AnswerPostProcessor()
concept_validator = ConceptValidator()
integrity_checker = IntegrityChecker()

# 定义降级错误类型
class ServiceUnavailableError(Exception):
    """服务不可用错误"""
    pass

class ModelFallbackError(Exception):
    """模型降级错误"""
    pass

class ServiceTimeoutError(Exception):
    """服务超时错误"""
    pass

# 创建路由器
router = APIRouter(prefix="/api/chat", tags=["Chat"])


# ========== 请求/响应模型 ==========

class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息", min_length=1)
    session_id: Optional[str] = Field(None, description="会话ID")
    stream: bool = Field(False, description="是否使用流式输出")
    config: Optional[Dict[str, Any]] = Field(None, description="额外配置")
    force_model: Optional[str] = Field(None, description="强制指定模型: '7b' 或 '14b'")


class ChatResponse(BaseModel):
    """聊天响应"""
    success: bool
    session_id: Optional[str] = None
    answer: str = ""
    reasoning: List[str] = []
    sources: List[Dict[str, Any]] = []
    confidence: float = 0.0
    metadata: Dict[str, Any] = {}
    error: Optional[str] = None

    # 双模型统计信息
    model_stats: Dict[str, Any] = {
        "model_used": None,
        "model_name": None,
        "complexity": None,
        "processing_time": None,
        "fallback_used": False,
        "retry_count": 0
    }


# ========== 辅助函数 ==========

def _get_chat_service_with_fallback():
    """获取聊天服务，带降级检查"""
    import sys
    import os

    # 检查是否启用 API 模式
    use_api = os.getenv("USE_DEEPSEEK_API", "false").lower() == "true"

    if use_api:
        # 使用 DeepSeek API
        try:
            from services.api_chat_service import get_api_chat_service
            chat_service = get_api_chat_service()
            logger.info("✅ 使用 DeepSeek API 服务")
            return chat_service
        except Exception as e:
            logger.warning(f"⚠️ API 服务初始化失败，尝试本地服务: {e}")
            # 降级到本地服务
            pass

    # 优先从 __main__ 获取
    main_module = sys.modules.get('__main__')
    chat_service = None

    if main_module:
        chat_service = getattr(main_module, '_chat_service', None)

    # 如果 __main__ 中没有，从服务模块获取
    if not chat_service:
        import services.chat_service as chat_module
        chat_service = getattr(chat_module, '_chat_service', None)

    # 健康检查
    try:
        if chat_service and hasattr(chat_service, 'is_ready') and not chat_service.is_ready():
            raise ServiceUnavailableError("聊天服务未就绪")
    except Exception as e:
        logger.warning(f"服务健康检查失败: {e}")
        raise ServiceUnavailableError(f"聊天服务不可用: {str(e)}")

    return chat_service


async def _handle_chat_with_retry(
    chat_service,
    message: str,
    session_id: str,
    chat_history: List[Dict[str, str]],
    config: Optional[Dict[str, Any]] = None,
    force_model: Optional[str] = None,
    retrieved_context: List[str] = None,
    max_retries: int = 2
):
    """带重试机制的聊天处理"""
    last_error = None
    retry_count = 0

    while retry_count <= max_retries:
        try:
            # 检查是否为双模型服务
            if hasattr(chat_service, 'achat'):
                import inspect
                sig = inspect.signature(chat_service.achat)
                if 'force_model' in sig.parameters:
                    result = await chat_service.achat(
                        message=message,
                        session_id=session_id,
                        chat_history=chat_history,
                        config=config,
                        force_model=force_model
                    )
                else:
                    result = await chat_service.achat(
                        message=message,
                        session_id=session_id,
                        chat_history=chat_history,
                        config=config
                    )
            else:
                # 检查 chat 方法是否是异步的
                import inspect
                if inspect.iscoroutinefunction(chat_service.chat):
                    # 异步方法（如 APIChatService），直接 await
                    result = await asyncio.wait_for(
                        chat_service.chat(
                            message=message,
                            chat_history=chat_history,
                            context=retrieved_context,  # 传递检索到的上下文
                            config=config
                        ),
                        timeout=60.0  # API 超时时间短一些
                    )
                else:
                    # 同步方法需要在线程池中运行
                    # 添加超时保护：32B 模型可能需要很长时间
                    try:
                        result = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: chat_service.chat(
                                    message=message,
                                    chat_history=chat_history,
                                    config=config
                                )
                            ),
                            timeout=600.0  # 10分钟超时
                        )
                    except asyncio.TimeoutError:
                        raise ServiceTimeoutError(f"聊天服务超时（>600秒），模型可能仍在推理中")

            # 检查结果是否成功
            if not result.get("success"):
                raise ModelFallbackError(result.get("error", "聊天服务返回错误"))

            return result, retry_count

        except ServiceUnavailableError as e:
            last_error = e
            raise  # 服务不可用不需要重试

        except (Exception, TimeoutError) as e:
            last_error = e
            retry_count += 1
            logger.warning(f"聊天处理失败 (尝试 {retry_count}/{max_retries}): {e}")

            if retry_count <= max_retries:
                # 最后一次重试尝试使用降级策略
                if retry_count == max_retries and hasattr(chat_service, '_select_model'):
                    try:
                        # 降级到7B模型
                        logger.info("尝试降级到7B模型...")
                        if force_model and force_model.lower() == "14b":
                            # 如果用户强制使用14B但失败了，尝试降级
                            if hasattr(chat_service, 'llm_14b') and chat_service.llm_14b is None:
                                result = await _handle_chat_with_retry(
                                    chat_service,
                                    message,
                                    session_id,
                                    chat_history,
                                    config,
                                    "7b",  # 强制降级到7B
                                    None,  # retrieved_context
                                    0  # 不再重试
                                )
                                result["fallback_used"] = True
                                return result, retry_count

                    except Exception as fallback_error:
                        logger.error(f"降级也失败: {fallback_error}")

            # 如果是最后一次重试，抛出错误
            if retry_count > max_retries:
                raise ServiceTimeoutError(f"聊天服务超时，已重试{max_retries}次: {str(e)}")


def _prepare_fallback_response(error: Exception) -> Dict[str, Any]:
    """准备降级响应"""
    if isinstance(error, ServiceUnavailableError):
        return {
            "success": False,
            "error": "服务暂时不可用，请稍后再试",
            "answer": "抱歉，AI服务正在维护中，请稍后再试。",
            "model_stats": {
                "fallback_used": True,
                "error_type": "service_unavailable"
            }
        }
    elif isinstance(error, ServiceTimeoutError):
        return {
            "success": False,
            "error": "请求超时，请重试",
            "answer": "抱歉，处理请求超时，请稍后重试。",
            "model_stats": {
                "fallback_used": True,
                "error_type": "timeout"
            }
        }
    elif isinstance(error, ModelFallbackError):
        return {
            "success": False,
            "error": "模型处理失败",
            "answer": "抱歉，AI模型暂时无法处理您的请求，请稍后再试。",
            "model_stats": {
                "fallback_used": True,
                "error_type": "model_error"
            }
        }
    else:
        return {
            "success": False,
            "error": str(error),
            "answer": "抱歉，系统出现未知错误，请稍后重试。",
            "model_stats": {
                "fallback_used": True,
                "error_type": "unknown"
            }
        }

# ========== API端点 ==========

@router.post("")  # 移除response_model，使用UTF8JSONResponse
async def chat(request: ChatRequest):
    """
    统一AI聊天接口

    这是前端唯一的AI交互入口。所有查询都通过此接口处理，
    后端会自动识别意图、调用合适的Agent、返回结果。

    ## 功能
    - 📚 文档搜索
    - 📊 表格查询
    - 🔍 对比分析
    - 🧮 费用计算
    - 📈 状态查询
    - 💬 通用问答
    - 🔄 自动降级：失败时自动重试并降级到7B模型
    - 📊 实时统计：包含模型使用统计和性能指标

    ## 示例
    ```json
    {
      "message": "59元套餐的分成比例是多少？",
      "session_id": "optional-session-id"
    }
    ```

    ## 响应
    ```json
    {
      "success": true,
      "answer": "根据渠道政策文档...",
      "reasoning": ["步骤1: 意图识别", "步骤2: 检索..."],
      "sources": [...],
      "confidence": 0.87,
      "model_stats": {
        "model_used": "14b",
        "model_name": "qwen2.5:32b",
        "complexity": {"score": 0.75, "intent": "analysis"},
        "processing_time": 2.3,
        "fallback_used": false,
        "retry_count": 0
      }
    }
    """
    start_time = time.time()

    try:
        # 获取聊天服务（带健康检查）
        chat_service = _get_chat_service_with_fallback()

        logger.info(f"[CHAT] 开始处理请求: session={request.session_id}, force_model={request.force_model}")

        # 向量检索知识库内容
        retrieved_context = []
        try:
            embedding_service = sys.modules.get('_embedding_service_instance')
            if embedding_service and getattr(embedding_service, 'model', None):
                from vector_storage import VectorStorage
                vector_storage = VectorStorage()
                if vector_storage.connect():
                    query_vector = embedding_service.embed_text(request.message)
                    search_results = vector_storage.search(
                        query_vector=query_vector,
                        top_k=20,  # 增加检索数量，提高信息完整性
                        score_threshold=0.3
                    )
                    if search_results:
                        retrieved_context = [
                            f'[来源: {r.get("source_document", "unknown")}, 相似度: {r.get("score", 0):.2f}]\n{r.get("text", "")}'
                            for r in search_results
                        ]
                        logger.info(f'🔍 向量检索到 {len(retrieved_context)} 条内容')
        except Exception as e:
            logger.warning(f'向量检索失败（非致命）: {e}')

        # 会话处理
        chat_history = []
        session_id_for_storage = request.session_id

        try:
            from routes.mobile_routes import _add_message_to_session, _get_or_create_session

            session_id = _get_or_create_session(request.session_id, "default_user")
            session_id_for_storage = session_id

            # 保存用户消息
            _add_message_to_session(session_id, role="user", content=request.message)

            # 获取历史对话
            from routes.mobile_routes import _sessions_storage
            if session_id in _sessions_storage:
                messages = _sessions_storage[session_id].get("messages", [])
                historical_messages = messages[:-1] if len(messages) > 0 else []
                chat_history = _prepare_chat_history(
                    historical_messages,
                    max_turns=5,
                    max_message_length=500
                )
                estimated_tokens = _calculate_history_tokens(chat_history)
                logger.info(f"📜 读取历史 {len(chat_history)} 条消息（约 {estimated_tokens} tokens）")

        except Exception as e:
            logger.warning(f"会话处理失败（非致命）: {e}")
            session_id = request.session_id or f"session_{int(time.time())}"

        # ========== 修复上下文连续性问题 ==========
        # 正确的顺序：
        # 1. 先保存当前用户消息到会话（这样AI回复也能被保存）
        # 2. 读取完整的聊天历史（包括刚保存的用户消息和之前的AI回复）
        # 3. 调用聊天服务

        chat_history = []
        session_id_for_storage = request.session_id

        # ========== 向量检索知识库内容 ==========
        retrieved_context = []
        search_results_dict = []  # 保存原始的检索结果（字典格式），用于完整性检查
        try:
            # 使用全局嵌入服务（已在应用启动时预加载）
            import sys
            embedding_service = sys.modules.get('_embedding_service_instance')

            if embedding_service is None or not getattr(embedding_service, 'model', None):
                # 如果全局服务不可用，记录警告并跳过向量检索
                logger.warning("⚠️ 嵌入服务未初始化，跳过向量检索")
            else:
                from vector_storage import VectorStorage
                vector_storage = VectorStorage()

                # 检查向量存储是否可用
                if vector_storage.connect():
                    # 生成查询向量
                    query_vector = embedding_service.embed_text(request.message)

                    # 执行向量搜索
                    search_results = vector_storage.search(
                        query_vector=query_vector,
                        top_k=20,  # 增加检索数量，提高信息完整性
                        score_threshold=0.3
                    )

                    if search_results:
                        # 保存原始检索结果（字典格式）
                        search_results_dict = search_results

                        for result in search_results:
                            text = result.get('text', '')
                            score = result.get('score', 0)
                            source = result.get('source_document', 'unknown')
                            retrieved_context.append(f'[来源: {source}, 相似度: {score:.2f}]\n{text}')
                            logger.info(f'🔍 检索到相关内容: {source}, score={score:.3f}, text_len={len(text)}')

                        logger.info(f'✅ 向量检索到 {len(retrieved_context)} 条相关文档片段')
                    else:
                        logger.info('ℹ️ 向量检索未找到相关文档')
                else:
                    logger.warning('⚠️ 向量存储未连接，跳过知识库检索')

        except Exception as e:
            logger.warning(f'向量检索失败（非致命）: {e}')
            import traceback
            logger.warning(traceback.format_exc())

        # 先获取或创建会话，并保存用户消息
        try:
            from routes.mobile_routes import _add_message_to_session, _get_or_create_session

            # 获取或创建会话
            session_id = _get_or_create_session(request.session_id, "default_user")
            session_id_for_storage = session_id

            # 先保存用户消息到会话（这样后续读取历史时能包含之前的完整对话）
            _add_message_to_session(
                session_id,
                role="user",
                content=request.message
            )

            # 然后读取该会话的完整历史对话（取最近5轮，包含之前AI的回复）
            from routes.mobile_routes import _sessions_storage
            if session_id in _sessions_storage:
                messages = _sessions_storage[session_id].get("messages", [])
                # 排除刚保存的当前用户消息（因为当前消息会作为 user_query 单独传递）
                historical_messages = messages[:-1] if len(messages) > 0 else []

                # 使用智能对话历史处理函数
                chat_history = _prepare_chat_history(
                    historical_messages,
                    max_turns=10,  # 增加到10轮，支持更深入的追问
                    max_message_length=1000  # 增加到1000字符，保留更多上下文
                )

                # 记录 token 估算
                estimated_tokens = _calculate_history_tokens(chat_history)
                logger.info(f"📜 从会话 {session_id} 读取了 {len(chat_history)} 条历史消息（约 {estimated_tokens} tokens）")

        except Exception as e:
            logger.warning(f"会话处理失败（非致命）: {e}")
            # 降级：使用传入的 session_id
            session_id = request.session_id or f"session_{int(time.time())}"

        # 使用增强的错误处理和重试机制处理聊天请求
        try:
            result, retry_count = await _handle_chat_with_retry(
                chat_service,
                message=request.message,
                session_id=session_id,
                chat_history=chat_history,
                config=request.config,
                force_model=request.force_model,
                retrieved_context=retrieved_context  # 传递检索到的上下文
            )

            # ===== 后处理流程 ======
            # 类型检查
            logger.info(f"🔍 result 类型: {type(result)}, 是否为字典: {isinstance(result, dict)}")
            if not isinstance(result, dict):
                logger.error(f"❌ result 不是字典: {result}")
                raise ValueError(f"Expected dict, got {type(result)}")

            # 提取原始答案
            logger.info(f"🔍 准备提取 answer 字段...")
            original_answer = result.get("answer", "")
            logger.info(f"🔍 original_answer 类型: {type(original_answer)}, 长度: {len(original_answer) if isinstance(original_answer, str) else 'N/A'}")

            # 去重处理
            logger.info(f"🔍 开始去重处理...")
            try:
                processed_answer = post_processor.process(original_answer)
                logger.info(f"🔍 processed_answer 类型: {type(processed_answer)}")
            except Exception as e:
                logger.error(f"❌ post_processor.process 失败: {e}")
                raise

            # P0: 2. 概念验证
            logger.info(f"🔍 开始概念验证...")
            try:
                validation_result = concept_validator.validate(
                    processed_answer,
                    context={"question": request.message, "sources": result.get("sources", [])}
                )
                logger.info(f"🔍 validation_result 类型: {type(validation_result)}")
            except Exception as e:
                logger.error(f"❌ concept_validator.validate 失败: {e}")
                raise

            # 记录验证结果
            if not validation_result["valid"]:
                logger.warning(f"⚠️ 概念验证发现问题: {validation_result['issues']}")
            if validation_result["warnings"]:
                logger.info(f"ℹ️ 概念验证警告: {validation_result['warnings']}")

            # P1: 3. 完整性检查
            logger.info(f"🔍 开始完整性检查...")
            try:
                integrity_result = integrity_checker.check(
                    question=request.message,
                    answer=processed_answer,
                    context=search_results_dict  # 使用原始的字典格式检索结果
                )
                logger.info(f"🔍 integrity_result 类型: {type(integrity_result)}")
            except Exception as e:
                logger.error(f"❌ integrity_checker.check 失败: {e}")
                raise

            if not integrity_result["passed"]:
                logger.warning(f"⚠️ 完整性检查发现问题: {integrity_result['missing_info']}")
            if integrity_result["warnings"]:
                logger.info(f"ℹ️ 完整性检查警告: {integrity_result['warnings']}")

            logger.info(f"✅ 完整性分数: {integrity_result['confidence']}")

            # 更新答案
            result["answer"] = processed_answer

            # 收集所有验证信息
            all_warnings = {}
            if validation_result["issues"] or validation_result["warnings"]:
                all_warnings["concept_validation"] = {
                    "issues": validation_result["issues"],
                    "warnings": validation_result["warnings"]
                }
            if not integrity_result["passed"] or integrity_result["warnings"]:
                all_warnings["integrity_check"] = {
                    "missing_info": integrity_result["missing_info"],
                    "warnings": integrity_result["warnings"],
                    "confidence": integrity_result["confidence"]
                }

            # 如果有问题，添加到响应中供前端显示
            if all_warnings:
                result["validation_warnings"] = all_warnings
            # ===== 后处理结束 =====

            # 记录统计信息
            processing_time = time.time() - start_time

            # 更新模型统计信息
            model_stats = {
                "model_used": result.get("model_used"),
                "model_name": result.get("model_name"),
                "complexity": result.get("complexity"),
                "processing_time": round(processing_time, 2),
                "fallback_used": False,  # 如果重试成功但不使用降级，则为false
                "retry_count": retry_count
            }

            # 检查是否使用了降级
            if retry_count > 0:
                model_stats["fallback_used"] = True
                logger.info(f"🔄 使用了降级策略，重试次数: {retry_count}")

        except ServiceUnavailableError as e:
            logger.error(f"服务不可用: {e}")
            fallback_response = _prepare_fallback_response(e)
            model_stats = fallback_response["model_stats"]
            result = fallback_response
        except ServiceTimeoutError as e:
            logger.error(f"服务超时: {e}")
            fallback_response = _prepare_fallback_response(e)
            model_stats = fallback_response["model_stats"]
            result = fallback_response
        except ModelFallbackError as e:
            logger.error(f"模型失败: {e}")
            fallback_response = _prepare_fallback_response(e)
            model_stats = fallback_response["model_stats"]
            result = fallback_response
        except Exception as e:
            logger.error(f"未知错误: {e}")
            fallback_response = _prepare_fallback_response(e)
            model_stats = fallback_response["model_stats"]
            result = fallback_response

        # 保存AI回答到会话存储
        try:
            from routes.mobile_routes import _add_message_to_session

            _add_message_to_session(
                session_id_for_storage,
                role="assistant",
                content=result.get("answer", ""),
                reasoning=result.get("reasoning", []),
                sources=result.get("sources", []),
                confidence=result.get("confidence", 0)
            )

            result["session_id"] = session_id_for_storage

        except Exception as e:
            logger.warning(f"保存AI回答失败（非致命）: {e}")

        # 更新响应中的模型统计信息
        if "model_stats" not in result:
            result["model_stats"] = model_stats

        # 记录处理完成日志
        processing_time = time.time() - start_time
        logger.info(
            f"✅ 聊天完成: success={result['success']}, "
            f"model={result.get('model_used', 'unknown')}, "
            f"time={processing_time:.2f}s, "
            f"fallback={model_stats.get('fallback_used', False)}"
        )

        # 去掉推理过程，前端不需要显示
        if "reasoning" in result:
            del result["reasoning"]

        # 使用UTF8JSONResponse确保中文正确显示
        from main import UTF8JSONResponse
        return UTF8JSONResponse(content=result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"聊天请求失败: {e}")
        # 返回降级响应而不是直接抛出HTTPException
        fallback_response = _prepare_fallback_response(e)
        from main import UTF8JSONResponse
        return UTF8JSONResponse(content=fallback_response)


@router.get("/health")
async def health_check():
    """
    健康检查

    检查聊天服务和各组件的状态，包含详细的降级信息
    """
    try:
        import services.dual_model_service as dual_module
        import services.chat_service as chat_module

        chat_service = getattr(dual_module, '_dual_model_service', None)
        if not chat_service or not hasattr(chat_service, 'master_graph_7b') or not chat_service.master_graph_7b:
            chat_service = getattr(chat_module, '_chat_service', None)

        status = chat_service.health_check() if chat_service else {"initialized": False}

        # 构建响应
        response = {
            "status": "healthy" if status.get("initialized", False) else "unhealthy",
            "service": type(chat_service).__name__ if chat_service else "None",
            "timestamp": time.time(),
            "version": "2.0"
        }

        # 添加详细状态
        if status.get("initialized"):
            response.update({
                "components": status.get("components", {}),
                "statistics": status.get("statistics", {}),
                "recommendations": []
            })

            # 检查组件健康状态
            components = status.get("components", {})
            if components.get("llm_14b", {}).get("status") == "not_configured":
                response["recommendations"].append("14B模型未配置，将自动降级到7B模型")
            if components.get("master_graph_14b", {}).get("status") == "not_configured":
                response["recommendations"].append("14B图未初始化，复杂查询将使用7B模型")

        return response

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time(),
            "recommendations": ["请检查服务日志"]
        }


@router.get("/stats")
async def get_stats():
    """
    获取双模型使用统计

    返回模型使用分布和统计信息，包含性能指标
    """
    try:
        import services.dual_model_service as dual_module
        import services.chat_service as chat_module

        chat_service = getattr(dual_module, '_dual_model_service', None)
        if not chat_service or not hasattr(chat_service, 'master_graph_7b') or not chat_service.master_graph_7b:
            chat_service = getattr(chat_module, '_chat_service', None)

        if chat_service and hasattr(chat_service, 'get_statistics'):
            stats = chat_service.get_statistics()

            # 添加额外统计信息
            enhanced_stats = {
                "basic_stats": stats,
                "model_distribution": {
                    "7b_percent": round(stats["7b_count"] / max(stats["total_count"], 1) * 100, 1),
                    "14b_percent": stats["14b_ratio"],
                    "total_requests": stats["total_count"]
                },
                "performance": {
                    "avg_complexity": stats["avg_complexity"],
                    "complexity_trend": "increasing" if stats["avg_complexity"] > 0.5 else "stable"
                },
                "system_info": {
                    "dual_mode_enabled": bool(chat_service.llm_14b),
                    "fallback_available": True,
                    "last_updated": time.time()
                }
            }

            return {
                "success": True,
                "data": enhanced_stats,
                "message": "双模型模式运行正常"
            }
        else:
            return {
                "success": True,
                "message": "当前为单模型模式",
                "data": {
                    "mode": "single_model",
                    "basic_stats": {
                        "total_requests": 0,
                        "avg_complexity": 0.0
                    }
                }
            }

    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "fallback_data": {
                "mode": "error",
                "error_message": str(e)
            }
        }


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天接口（可选功能）

    使用Server-Sent Events (SSE)实时返回Agent的思考过程。
    这允许前端实时显示Agent的推理步骤。

    注意：此功能为可选项，当前版本返回与普通聊天相同的结果。
    """
    # 流式输出是高级功能，当前版本暂不实现
    # 直接调用普通聊天接口
    return await chat(request)


@router.get("/conversations")
async def get_conversations():
    """
    获取会话历史列表

    返回所有历史会话记录，用于侧边栏显示。

    ## 返回
    ```json
    {
      "success": true,
      "data": [
        {
          "id": "session_id",
          "title": "对话标题",
          "preview": "预览内容",
          "timestamp": "2024-01-01T00:00:00",
          "messageCount": 5
        }
      ]
    }
    ```
    """
    try:
        # 从 mobile_routes 的会话存储中获取数据
        from routes.mobile_routes import _sessions_storage, _user_sessions

        user_id = "default_user"
        session_ids = _user_sessions.get(user_id, [])

        conversations = []
        for session_id in session_ids:
            if session_id in _sessions_storage:
                session = _sessions_storage[session_id]
                messages = session.get("messages", [])

                # 生成标题（取第一条用户消息）
                title = "新对话"
                preview = ""
                for msg in messages:
                    if msg.get("role") == "user":
                        content = msg.get("content", "")
                        title = content[:30]
                        if len(content) > 30:
                            title += "..."
                        preview = content[:100]
                        if len(content) > 100:
                            preview += "..."
                        break

                conversations.append({
                    "id": session_id,
                    "title": title,
                    "preview": preview,
                    "timestamp": session.get("updated_at", session.get("created_at")),
                    "messageCount": len(messages)
                })

        return {
            "success": True,
            "data": conversations
        }

    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        return {
            "success": True,
            "data": [],
            "message": f"获取会话列表失败: {str(e)}"
        }


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """
    获取会话的消息历史

    返回指定会话的所有消息，用于恢复历史对话。

    ## 参数
    - conversation_id: 会话ID

    ## 返回
    ```json
    {
      "success": true,
      "data": {
        "id": "session_id",
        "messages": [...]
      }
    }
    ```
    """
    try:
        from routes.mobile_routes import _sessions_storage

        if conversation_id not in _sessions_storage:
            return {
                "success": False,
                "error": "会话不存在"
            }

        session = _sessions_storage[conversation_id]
        messages = session.get("messages", [])

        # 转换消息格式以匹配前端期望的格式
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "id": msg.get("message_id", ""),
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
                "timestamp": msg.get("timestamp", ""),
                "sources": msg.get("sources", []),
                "relevanceScore": msg.get("confidence", 0),
                "reasoning": msg.get("reasoning", [])
            })

        return {
            "success": True,
            "data": {
                "id": conversation_id,
                "messages": formatted_messages
            }
        }

    except Exception as e:
        logger.error(f"获取会话消息失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# 批量删除路由必须放在单个删除之前，否则"batch"会被当作conversation_id参数处理
class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: List[str] = Field(..., description="要删除的会话ID列表")


@router.delete("/conversations/batch")
async def batch_delete_conversations(http_request: Request):
    """
    批量删除会话

    批量删除多个会话及其所有消息。
    """
    try:
        # 从请求体获取数据
        body = await http_request.json()
        ids = body.get("ids", [])

        if not ids:
            return {
                "success": False,
                "error": "缺少ids参数"
            }

        from routes.mobile_routes import _sessions_storage, _user_sessions

        deleted_count = 0
        failed_ids = []

        for conversation_id in ids:
            try:
                # 检查会话是否存在
                if conversation_id not in _sessions_storage:
                    logger.warning(f"会话不存在: {conversation_id}")
                    failed_ids.append(conversation_id)
                    continue

                # 获取会话的user_id（从会话数据中获取，与单个删除逻辑一致）
                session = _sessions_storage[conversation_id]
                user_id = session.get("user_id", "default_user")

                # 从用户索引中移除
                if user_id in _user_sessions:
                    if conversation_id in _user_sessions[user_id]:
                        _user_sessions[user_id].remove(conversation_id)

                # 删除会话
                del _sessions_storage[conversation_id]
                deleted_count += 1
                logger.info(f"已删除会话: {conversation_id}")

            except Exception as e:
                logger.warning(f"删除会话 {conversation_id} 失败: {e}")
                failed_ids.append(conversation_id)

        # 如果全部失败，返回失败
        if deleted_count == 0:
            return {
                "success": False,
                "error": "没有删除任何会话",
                "deleted_count": 0,
                "failed_ids": failed_ids
            }

        return {
            "success": True,
            "message": f"已删除{deleted_count}个会话",
            "deleted_count": deleted_count,
            "failed_ids": failed_ids
        }

    except Exception as e:
        logger.error(f"批量删除会话失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "deleted_count": 0,
            "failed_ids": ids
        }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    删除会话

    删除指定的会话及其所有消息。

    ## 参数
    - conversation_id: 会话ID

    ## 返回
    ```json
    {
      "success": true,
      "message": "会话已删除"
    }
    ```
    """
    try:
        from routes.mobile_routes import _sessions_storage, _user_sessions

        if conversation_id not in _sessions_storage:
            return {
                "success": False,
                "error": "会话不存在"
            }

        # 从用户索引中移除
        session = _sessions_storage[conversation_id]
        user_id = session.get("user_id", "default_user")

        if user_id in _user_sessions:
            if conversation_id in _user_sessions[user_id]:
                _user_sessions[user_id].remove(conversation_id)

        # 删除会话
        del _sessions_storage[conversation_id]

        return {
            "success": True,
            "message": "会话已删除"
        }

    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ========== 对话历史处理辅助函数 ==========

def _prepare_chat_history(
    messages: list,
    max_turns: int = 5,
    max_message_length: int = 500
) -> list:
    """
    智能准备对话历史 - 优化多轮对话支持

    策略：
    1. 优先保留最近几轮的完整对话（用户+助手成对）
    2. 智能压缩：保留关键信息，优先保留数字和专有名词
    3. 上下文保持：确保追问时能理解之前的内容
    4. 移除冗余：避免重复信息占用token

    Args:
        messages: 原始消息列表
        max_turns: 最大保留轮数（默认5轮）
        max_message_length: 单条消息最大长度（超过则智能压缩）

    Returns:
        处理后的对话历史列表
    """
    if not messages:
        return []

    processed = []

    # 按轮次组织消息（用户消息后跟对应的助手回复）
    turns = []
    current_turn = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "").strip()

        # 跳过空消息
        if not content:
            continue

        # 只保留用户和助手消息
        if role not in ["user", "assistant"]:
            continue

        current_turn.append({"role": role, "content": content})

        # 当收集到完整一轮（用户+助手）后，保存这一轮
        if len(current_turn) == 2 or (len(current_turn) == 1 and role == "user"):
            turns.append(list(current_turn))
            # 如果是用户消息结尾，保留在下一轮继续匹配
            if role == "user":
                current_turn = [{"role": role, "content": content}]
            else:
                current_turn = []

    # 处理剩余的未配对消息
    if current_turn:
        turns.append(current_turn)

    # 取最近 N 轮对话
    recent_turns = turns[-max_turns:] if len(turns) > max_turns else turns

    # 展开并智能压缩消息
    for turn in recent_turns:
        for msg in turn:
            content = msg["content"]

            # 智能压缩过长消息
            if len(content) > max_message_length:
                content = _intelligent_compress(content, max_message_length)

            processed.append({
                "role": msg["role"],
                "content": content
            })

    # 添加对话上下文摘要（如果有多轮对话）
    if len(recent_turns) > 3:
        context_summary = _build_context_summary(recent_turns)
        if context_summary:
            logger.info(f"💬 对话上下文摘要: {context_summary}")

    logger.info(f"📝 对话历史处理: 原始{len(messages)}条 -> 压缩后{len(processed)}条 ({len(recent_turns)}轮)")

    return processed


def _intelligent_compress(text: str, max_length: int) -> str:
    """
    智能压缩文本，保留关键信息

    优先保留：
    1. 数字和单位（如 10GB、59元）
    2. 专有名词（大写字母、特殊标记）
    3. 句子的开头和结尾
    """
    if len(text) <= max_length:
        return text

    # 尝试按句子分割
    import re
    sentences = re.split(r'[。！？\n]', text)

    if len(sentences) <= 1:
        # 没有句子分割，直接截断
        half_length = max_length // 2
        return text[:half_length] + "..." + text[-half_length:]

    # 保留重要句子（包含数字、单位、专有名词的句子优先）
    important_sentences = []
    other_sentences = []

    for sent in sentences:
        if not sent.strip():
            continue
        # 检查是否包含重要信息
        if re.search(r'\d+[A-Za-z]+|\d+[元美]|【|」|\d+GB|\d+MB', sent):
            important_sentences.append(sent.strip())
        else:
            other_sentences.append(sent.strip())

    # 优先保留重要句子
    result_sentences = important_sentences + other_sentences
    result = ''
    for sent in result_sentences:
        if len(result) + len(sent) + 1 <= max_length:
            result += sent + '。'
        else:
            break

    if len(result) < max_length // 2:
        # 如果压缩后太短，使用简单截断
        half_length = max_length // 2
        result = text[:half_length] + "..." + text[-half_length:]

    return result


def _build_context_summary(turns: list) -> str:
    """
    构建对话上下文摘要

    提取之前对话中的关键主题，帮助AI理解上下文
    """
    if not turns:
        return ""

    # 提取用户问题中的关键词
    keywords = []
    for turn in turns[:-1]:  # 不包括最近一轮
        for msg in turn:
            if msg["role"] == "user":
                # 提取关键词（简单的名词提取）
                import re
                content = msg["content"]
                # 提取可能的主题词
                words = re.findall(r'[\u4e00-\u9fa5]{2,4}', content)
                keywords.extend(words[:3])  # 每轮最多取3个关键词

    # 去重并限制数量
    unique_keywords = list(dict.fromkeys(keywords))[:5]

    if unique_keywords:
        return f"之前讨论了: {', '.join(unique_keywords)}"

    return ""


def _calculate_history_tokens(chat_history: list) -> int:
    """
    估算对话历史的 token 数量

    简单估算：中文约 1.5 字符 = 1 token，英文约 4 字符 = 1 token
    """
    total_chars = sum(len(msg.get("content", "")) for msg in chat_history)
    # 混合估算：假设中英文混合
    estimated_tokens = int(total_chars / 2)
    return estimated_tokens

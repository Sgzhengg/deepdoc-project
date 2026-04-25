# main.py - 极简长上下文架构 - 重构版
import io
import json
import logging
import os
import sys
import tempfile
import uuid
import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from contextlib import asynccontextmanager

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Request, Depends, Header
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.encoders import jsonable_encoder

# 导入安全配置
from config.security import verify_api_key, verify_ip_access, check_rate_limit, get_client_ip, skip_api_key_verification, VALID_API_KEYS

# 根据环境变量选择API密钥验证函数
def get_api_key_dependency():
    """根据配置返回适当的API密钥验证依赖"""
    logger.info(f"🔍 get_api_key_dependency调用: VALID_API_KEYS={VALID_API_KEYS}")
    if not VALID_API_KEYS:
        logger.info("✅ 使用skip_api_key_verification")
        return skip_api_key_verification
    logger.info("✅ 使用verify_api_key")
    return verify_api_key

api_key_dependency = get_api_key_dependency()

# ========== 创建FastAPI应用 ==========

# 全局服务实例
_long_context_service = None
_data_dir = None

# 内存会话存储
_conversations: Dict[str, List[Dict]] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _long_context_service, _data_dir

    # 启动时初始化服务
    logger.info("🚀 DeepDoc API启动中（极简长上下文架构）...")

    try:
        from services.simple_long_context_service import SimpleLongContextService

        # 初始化服务
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        _long_context_service = SimpleLongContextService(deepseek_api_key=deepseek_api_key)

        # 加载数据目录
        data_dir = os.getenv("DATA_DIR", "data")
        _data_dir = Path(data_dir)

        if _data_dir.exists():
            count = _long_context_service.load_documents(str(_data_dir))
            stats = _long_context_service.get_stats()
            logger.info(f"✅ 服务初始化完成：加载了 {count} 个文档，总计 {stats['total_words']} 字")
        else:
            logger.warning(f"⚠️ 数据目录不存在: {data_dir}，将等待文档上传")
            # 创建数据目录
            _data_dir.mkdir(parents=True, exist_ok=True)

        # 注册到全局
        sys.modules['_long_context_service_instance'] = _long_context_service

    except Exception as e:
        logger.error(f"❌ 服务初始化失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        _long_context_service = None

    yield  # 应用运行

    # 关闭时清理资源
    logger.info("👋 DeepDoc API关闭中...")
    _long_context_service = None
    logger.info("✅ DeepDoc API已安全关闭")

app = FastAPI(
    title="DeepDoc API - 极简长上下文版本",
    description="极简文档管理系统，基于长上下文 + DeepSeek API",
    version="2.0.0",
    lifespan=lifespan
)

# 自定义JSON响应类
class UTF8JSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            jsonable_encoder(content),
            ensure_ascii=False,
            allow_nan=True,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

# CORS中间件
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = allowed_origins_str.split(",") if allowed_origins_str != "*" else ["*"]

if "*" in allowed_origins:
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ========== 辅助函数 ==========

def get_service():
    """获取服务实例"""
    global _long_context_service
    if _long_context_service is None:
        raise HTTPException(status_code=503, detail="服务未初始化")
    return _long_context_service

# ========== API端点 ==========

@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        service = get_service()
        stats = service.get_stats()
        return {
            "status": "healthy",
            "service": "long_context",
            "documents_loaded": stats["total_documents"],
            "total_words": stats["total_words"],
            "deepseek_configured": bool(service.deepseek_api_key)
        }
    except HTTPException:
        return {
            "status": "unhealthy",
            "service": "long_context",
            "documents_loaded": 0
        }

@app.post("/api/chat")
async def chat_endpoint(
    request: Request
):
    """智能问答接口（基于文档检索 + DeepSeek API）"""
    logger.info(f"🔧 chat_endpoint被调用，VALID_API_KEYS={VALID_API_KEYS}")
    try:
        # API密钥验证（如果配置了）
        if VALID_API_KEYS:
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                raise HTTPException(
                    status_code=401,
                    detail="API密钥缺失，请在请求头中提供 X-API-Key"
                )
            if api_key not in VALID_API_KEYS:
                raise HTTPException(
                    status_code=403,
                    detail="无效的API密钥"
                )
        else:
            logger.info("🔓 跳过API密钥验证")

        # IP访问验证
        client_ip = get_client_ip(request)
        await verify_ip_access(client_ip)

        # 请求频率限制
        await check_rate_limit(client_ip)

        # 安全地获取请求体
        try:
            body = await request.json()
        except UnicodeDecodeError:
            body_bytes = await request.body()
            body = json.loads(body_bytes.decode('utf-8', errors='ignore'))

        message = body.get("message", "").strip()
        session_id = body.get("session_id", str(uuid.uuid4()))

        if not message:
            raise HTTPException(status_code=400, detail="消息不能为空")

        service = get_service()

        # 初始化会话（如果不存在）
        if session_id not in _conversations:
            _conversations[session_id] = []

        # 获取历史对话（不包括当前消息，用于API调用）
        conversation_history = _conversations[session_id].copy()

        # 保存用户消息
        _conversations[session_id].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.datetime.now().isoformat()
        })

        # 真正的长上下文架构：直接发送所有文档给 DeepSeek API，包含对话历史
        result = service.ask_deepseek_long_context(message, conversation_history)

        # 保存助手回复
        _conversations[session_id].append({
            "role": "assistant",
            "content": result["answer"],
            "timestamp": datetime.datetime.now().isoformat()
        })

        # 添加会话ID到结果
        result["session_id"] = session_id
        result["question"] = message
        result["timestamp"] = datetime.datetime.now().isoformat()

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 聊天失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest")
async def ingest_document(
    request: Request,
    file: UploadFile = File(...)
):
    """文档入库到知识库"""
    try:
        # API密钥验证（如果配置了）
        if VALID_API_KEYS:
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                raise HTTPException(
                    status_code=401,
                    detail="API密钥缺失，请在请求头中提供 X-API-Key"
                )
            if api_key not in VALID_API_KEYS:
                raise HTTPException(
                    status_code=403,
                    detail="无效的API密钥"
                )
        else:
            logger.info("🔓 跳过API密钥验证")
        # IP访问验证
        client_ip = get_client_ip(request)
        await verify_ip_access(client_ip)

        # 请求频率限制
        await check_rate_limit(client_ip)

        service = get_service()

        # 保存上传的文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        # 处理文档
        doc_name = file.filename
        doc_path = Path(tmp_path)

        # 根据文件类型解析
        if doc_path.suffix.lower() == '.docx':
            text, metadata = service._parse_docx_enhanced(doc_path)
        elif doc_path.suffix.lower() in ['.xlsx', '.xls']:
            text, metadata = service._parse_xlsx_enhanced(doc_path)
        else:
            raise HTTPException(status_code=400, detail="仅支持 DOCX 和 XLSX 格式")

        # 添加到文档库
        service.add_document(doc_name, text, metadata)

        # 保存到数据目录
        if _data_dir and _data_dir.exists():
            save_path = _data_dir / doc_name
            import shutil
            shutil.copy2(doc_path, save_path)

        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except:
            pass

        return {
            "success": True,
            "message": "文档入库成功",
            "document": {
                "filename": doc_name,
                "content_length": len(text),
                "metadata": metadata
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 文档入库失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents")
async def get_documents_list():
    """获取文档列表"""
    try:
        service = get_service()
        stats = service.get_stats()

        documents = []
        for doc_name in stats["documents"]:
            metadata = service.document_metadata.get(doc_name, {})
            documents.append({
                "id": doc_name,
                "filename": doc_name,
                "upload_date": datetime.datetime.now().isoformat(),
                "word_count": metadata.get('word_count', 0),
                "table_count": len(metadata.get('tables', [])),
                "source": "long_context"
            })

        return {
            "success": True,
            "data": documents,
            "count": len(documents)
        }
    except Exception as e:
        logger.error(f"❌ 获取文档列表失败: {e}")
        return {"success": False, "error": str(e), "data": [], "count": 0}

@app.delete("/api/documents/{doc_id}")
async def delete_document(doc_id: str):
    """删除文档"""
    try:
        service = get_service()

        if doc_id in service.documents:
            service.remove_document(doc_id)

            # 删除文件
            if _data_dir and _data_dir.exists():
                doc_path = _data_dir / doc_id
                if doc_path.exists():
                    doc_path.unlink()

            return {"success": True, "message": "文档已删除"}
        else:
            raise HTTPException(status_code=404, detail="文档不存在")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/kb/status")
async def get_kb_status():
    """获取知识库状态"""
    try:
        service = get_service()
        stats = service.get_stats()

        # 计算总大小
        total_size = 0
        file_list = []
        if _data_dir and _data_dir.exists():
            for f in _data_dir.glob("*.docx"):
                size = f.stat().st_size
                total_size += size
                file_list.append({"name": f.name, "size": size})
            for f in _data_dir.glob("*.xlsx"):
                size = f.stat().st_size
                total_size += size
                file_list.append({"name": f.name, "size": size})

        return {
            "success": True,
            "mode": "long_context",
            "status": "active",
            "total_documents": stats["total_documents"],
            "total_words": stats["total_words"],
            "total_tables": stats["total_tables"],
            "total_size": total_size,
            "documents": file_list,
            "deepseek_configured": bool(service.deepseek_api_key)
        }
    except Exception as e:
        logger.error(f"❌ 获取知识库状态失败: {e}")
        return {"success": False, "error": str(e)}

@app.delete("/api/kb/clear")
async def clear_kb():
    """清空知识库"""
    try:
        service = get_service()

        service.documents.clear()
        service.document_metadata.clear()

        if _data_dir and _data_dir.exists():
            for file in _data_dir.glob("*.docx"):
                file.unlink(missing_ok=True)
            for file in _data_dir.glob("*.xlsx"):
                file.unlink(missing_ok=True)

        return {"success": True, "message": "知识库已清空"}
    except Exception as e:
        logger.error(f"❌ 清空知识库失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations")
async def get_conversations():
    """获取会话列表"""
    try:
        conversations = []
        for session_id, messages in _conversations.items():
            if messages:
                first_msg = messages[0]
                last_msg = messages[-1]

                # 获取最后一条消息作为预览
                preview = ""
                if last_msg.get('content'):
                    preview = last_msg.get('content', '')[:100] + ('...' if len(last_msg.get('content', '')) > 100 else '')
                # 如果是助手回复，尝试从用户消息中获取预览
                elif len(messages) > 1:
                    preview = messages[-2].get('content', '')[:100] + ('...' if len(messages[-2].get('content', '')) > 100 else '')

                conversations.append({
                    "id": session_id,
                    "title": first_msg.get('content', '新对话')[:30] + ('...' if len(first_msg.get('content', '')) > 30 else ''),
                    "preview": preview,
                    "created_at": first_msg.get('timestamp', datetime.datetime.now().isoformat()),
                    "updated_at": last_msg.get('timestamp', datetime.datetime.now().isoformat()),
                    "message_count": len(messages)
                })

        return {
            "success": True,
            "data": conversations,
            "total": len(conversations)
        }
    except Exception as e:
        logger.error(f"❌ 获取会话列表失败: {e}")
        return {"success": False, "error": str(e), "data": [], "total": 0}

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除会话"""
    try:
        if conversation_id in _conversations:
            del _conversations[conversation_id]
            return {"success": True, "message": "会话已删除"}
        else:
            return {"success": False, "error": "会话不存在"}
    except Exception as e:
        logger.error(f"❌ 删除会话失败: {e}")
        return {"success": False, "error": str(e)}

@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """获取会话消息"""
    try:
        messages = _conversations.get(conversation_id, [])
        return {
            "success": True,
            "data": messages,
            "conversation_id": conversation_id
        }
    except Exception as e:
        logger.error(f"❌ 获取会话消息失败: {e}")
        return {"success": False, "error": str(e), "data": []}

# ========== 启动服务 ==========

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
@app.get("/api/debug/search")
async def debug_search(query: str = Query(..., description="搜索关键词")):
    """调试搜索过程"""
    try:
        service = get_service()
        print(f"[DEBUG] Service instance: {id(service)}")
        print(f"[DEBUG] Documents count: {len(service.documents)}")

        results = service.search_documents(query, top_k=5)
        print(f"[DEBUG] Search results count: {len(results)}")

        return {
            "success": True,
            "query": query,
            "service_id": id(service),
            "documents_count": len(service.documents),
            "search_results_count": len(results),
            "results": results
        }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
 }

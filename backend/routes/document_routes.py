"""
文档路由 - 文档入库和管理接口
"""

import logging
import tempfile
import os
import uuid
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/documents", tags=["Documents"])


def get_embedding_service():
    """获取嵌入服务实例（支持多个来源）"""
    # 来源1: dual_model_service
    import services.dual_model_service as dual_module
    dual_service = getattr(dual_module, '_dual_model_service', None)
    if dual_service and dual_service.hybrid_retriever:
        return dual_service.hybrid_retriever.embedding_service

    # 来源2: service_instance 模块
    import service_instance
    embedding_svc = service_instance.get_embedding_service()
    if embedding_svc:
        return embedding_svc

    # 来源3: main.py 中的全局实例
    import sys
    main_module = sys.modules.get('__main__') or sys.modules.get('main')
    if main_module:
        global_emb = getattr(main_module, '_embedding_service', None)
        if global_emb:
            return global_emb

    # 来源4: 尝试直接创建
    try:
        from embedding_service import EmbeddingService
        emb = EmbeddingService()
        if emb.load_model():
            logger.warning("⚠️ 使用临时创建的嵌入服务")
            return emb
    except Exception as e:
        logger.warning(f"无法创建临时嵌入服务: {e}")

    raise HTTPException(
        status_code=500,
        detail="嵌入服务未初始化，请确保后端服务已正确启动"
    )


def get_vector_storage():
    """获取向量存储服务实例（支持多个来源）"""
    # 来源1: dual_model_service
    import services.dual_model_service as dual_module
    dual_service = getattr(dual_module, '_dual_model_service', None)

    if dual_service and dual_service.hybrid_retriever:
        vs = dual_service.hybrid_retriever.vector_storage
        if vs and vs.connected:
            return vs

    # 来源2: service_instance 模块
    import service_instance
    vector_svc = service_instance.get_vector_storage()
    if vector_svc and vector_svc.connected:
        return vector_svc

    # 来源3: main.py 中的全局实例
    import sys
    main_module = sys.modules.get('__main__') or sys.modules.get('main')
    if main_module:
        global_vs = getattr(main_module, '_vector_storage', None)
        if global_vs and global_vs.connected:
            return global_vs

    # 来源4: 尝试直接创建
    try:
        from vector_storage import VectorStorage
        vs = VectorStorage()
        if vs.connect():
            logger.warning("⚠️ 使用临时创建的向量存储")
            return vs
    except Exception as e:
        logger.warning(f"无法创建临时向量存储: {e}")

    raise HTTPException(
        status_code=500,
        detail="向量存储服务未连接，请确保后端服务已正确启动"
    )


@router.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """
    文档入库接口

    上传并处理文档，自动进行：
    - 文档分析（PDF/Office）
    - 文本提取
    - 表格提取
    - 向量化
    - 存储到知识库

    ## 支持的格式
    - PDF (.pdf)
    - Word (.docx)
    - Excel (.xlsx)

    ## 返回
    ```json
    {
      "success": true,
      "document_id": "uuid",
      "filename": "document.pdf",
      "chunks_count": 42,
      "tables_extracted": 3,
      "status": "indexed"
    }
    ```
    """
    import time
    start_time = time.time()

    # 导入文档处理模块（延迟导入，避免循环导入）
    try:
        # 从main模块导入文档分析函数
        import sys
        main_module = sys.modules.get('__main__') or sys.modules.get('main')
        if not main_module or not hasattr(main_module, 'analyze_pdf_with_paddleocr'):
            raise ImportError("无法从main模块导入文档分析函数")

        analyze_pdf_with_paddleocr = main_module.analyze_pdf_with_paddleocr
        analyze_docx = main_module.analyze_docx
        analyze_xlsx = main_module.analyze_xlsx

    except ImportError as e:
        logger.error(f"导入文档分析模块失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"文档分析模块未正确加载: {str(e)}"
        )

    # 支持的文件类型和扩展名
    ALLOWED_MIME_TYPES = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "application/octet-stream": "auto"  # 自动检测
    }

    # 从文件名获取扩展名
    filename_lower = file.filename.lower()
    if filename_lower.endswith(".pdf"):
        file_ext = "pdf"
        mime_type = "application/pdf"
    elif filename_lower.endswith(".docx"):
        file_ext = "docx"
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif filename_lower.endswith(".xlsx") or filename_lower.endswith(".xls"):
        if filename_lower.endswith(".xls"):
            file_ext = "xls"
            mime_type = "application/vnd.ms-excel"
        else:
            file_ext = "xlsx"
            mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件扩展名: {file.filename}. 支持的格式: PDF, DOCX, XLSX, XLS"
        )

    file_size = 0
    logger.info(f"📤 上传文件: {file.filename}, 检测到类型: {file_ext}")

    temp_file = None
    doc_id = str(uuid.uuid4())

    try:
        # 步骤0: 读取上传文件
        read_start = time.time()
        contents = await file.read()
        file_size = len(contents)
        read_time = time.time() - read_start
        logger.info(f"📥 文件读取完成: {file_size:,} bytes ({read_time:.2f}s)")

        # 检查文件大小限制 (50MB)
        MAX_FILE_SIZE = 50 * 1024 * 1024
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件过大 ({file_size / 1024 / 1024:.1f}MB)。最大支持 50MB"
            )

        # 保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
            tmp.write(contents)
            temp_file = tmp.name

        logger.info(f"📄 开始处理文档: {file.filename} ({doc_id})")

        # 步骤1: 分析文档提取文本和表格
        analysis_start = time.time()
        logger.info(f"🔍 步骤1: 分析文档内容...")

        if file_ext == "pdf":
            analysis_result = analyze_pdf_with_paddleocr(temp_file)
        elif file_ext == "docx":
            analysis_result = analyze_docx(temp_file)
        elif file_ext == "xlsx" or file_ext == "xls":
            analysis_result = analyze_xlsx(temp_file)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_ext}")

        analysis_time = time.time() - analysis_start
        logger.info(f"✅ 文档分析完成 ({analysis_time:.2f}s)")

        # 提取全文（包括表格内容）
        full_text = ""
        for page in analysis_result.get("pages", []):
            # 添加段落文本
            full_text += page.get("text", "") + "\n\n"

            # 添加表格内容为文本格式，使表格可被检索
            tables = page.get("tables", [])
            if tables:
                full_text += "\n=== 表格内容 ===\n"
                for table_idx, table in enumerate(tables):
                    full_text += f"\n表格 {table_idx + 1}:\n"

                    # 获取表格数据
                    column_names = table.get("column_names", [])
                    data = table.get("data", [])

                    if column_names:
                        # 添加表头
                        full_text += "  表头: " + " | ".join(str(col) for col in column_names) + "\n"

                    # 添加表格数据
                    for row_idx, row in enumerate(data):
                        if isinstance(row, dict):
                            row_text = " | ".join(str(row.get(col, "")) for col in column_names)
                        else:
                            row_text = " | ".join(str(cell) for cell in row)
                        full_text += f"  行{row_idx + 1}: {row_text}\n"

                    full_text += "\n"

        full_text = full_text.strip()

        text_length = len(full_text)
        logger.info(f"📝 提取文本长度: {text_length:,} 字符（含表格内容）")

        if not full_text:
            raise HTTPException(
                status_code=400,
                detail="文档没有提取到文本内容，可能是扫描版PDF或图片文档"
            )

        # 步骤2: 文本分块
        chunk_start = time.time()
        logger.info(f"🔪 步骤2: 文本分块...")

        vector_storage = get_vector_storage()
        if not vector_storage or not vector_storage.connected:
            raise HTTPException(
                status_code=500,
                detail="向量存储服务未连接"
            )

        chunks = vector_storage.chunk_text(full_text)
        if not chunks:
            raise HTTPException(
                status_code=500,
                detail="文档分块失败"
            )

        chunk_time = time.time() - chunk_start
        logger.info(f"✅ 分块完成: {len(chunks)} 个分块 ({chunk_time:.2f}s)")

        # 步骤3: 向量化
        embed_start = time.time()
        logger.info(f"🔢 步骤3: 生成向量嵌入...")

        embedding_service = get_embedding_service()
        if not embedding_service:
            raise HTTPException(
                status_code=500,
                detail="嵌入服务未初始化"
            )

        embeddings = embedding_service.embed_batch(chunks)

        embed_time = time.time() - embed_start
        logger.info(f"✅ 向量化完成: {len(embeddings)} 个向量 ({embed_time:.2f}s)")

        # 步骤4: 存储到向量数据库
        store_start = time.time()
        logger.info(f"💾 步骤4: 存储到向量数据库...")

        # 计算总表格数（所有页面）
        total_tables = sum(len(page.get("tables", [])) for page in analysis_result.get("pages", []))

        metadata = {
            "doc_id": doc_id,
            "filename": file.filename,
            "file_size": file_size,
            "mime_type": mime_type,
            "ingested_at": datetime.now().astimezone().isoformat(),
            "total_chunks": len(chunks),
            "tables_extracted": total_tables
        }

        storage_result = vector_storage.store_document(
            doc_id,
            chunks,
            embeddings,
            metadata
        )

        if not storage_result.get("success"):
            error_msg = storage_result.get("error", "未知存储错误")
            logger.error(f"❌ 存储失败: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"存储文档到向量数据库失败: {error_msg}"
            )

        store_time = time.time() - store_start
        logger.info(f"✅ 存储完成: {storage_result.get('stored_chunks', 0)} 个分块 ({store_time:.2f}s)")

        # 步骤5: 如果有表格，加载到表格分析器
        tables_count = 0
        try:
            from agents.enhanced_table_analyzer import get_table_analyzer
            table_analyzer = get_table_analyzer()

            if file_ext == "docx":
                table_analyzer.load_from_docx(temp_file)
                tables_count = len(table_analyzer.get_table_summary())
            elif file_ext == "xlsx":
                table_analyzer.load_from_xlsx(temp_file)
                tables_count = len(table_analyzer.get_table_summary())

            logger.info(f"📊 提取到 {tables_count} 个表格")

            # 保存表格数据到缓存文件（重启后可恢复）
            if tables_count > 0:
                table_analyzer.save_tables_to_cache()

        except Exception as e:
            logger.warning(f"⚠️ 表格加载失败（非致命）: {e}")

        # 计算总处理时间
        total_time = time.time() - start_time
        logger.info(f"🎉 文档 {file.filename} 入库完成! 总耗时: {total_time:.2f}s")

        # 返回成功结果
        return {
            "success": True,
            "document_id": doc_id,
            "filename": file.filename,
            "chunks_count": len(chunks),
            "tables_extracted": tables_count,
            "stored_chunks": storage_result.get("stored_chunks", 0),
            "status": "indexed",
            "processing_time": round(total_time, 2),
            "message": f"文档 {file.filename} 已成功入库"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档入库失败: {e}")
        import traceback
        logger.error(f"详细错误堆栈:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"文档入库失败: {str(e)}"
        )
    finally:
        # 清理临时文件（忽略错误，因为文件可能被其他进程锁定）
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except PermissionError:
                # Windows下文件可能被Excel进程锁定，延迟后重试
                import time
                time.sleep(0.5)
                try:
                    os.unlink(temp_file)
                except:
                    logger.warning(f"无法删除临时文件 {temp_file}，将在系统清理时删除")
            except Exception as e:
                logger.warning(f"删除临时文件失败: {e}")


@router.get("/status")
async def get_documents_status():
    """
    获取知识库状态

    返回向量数据库中的文档统计信息
    """
    try:
        vector_storage = get_vector_storage()

        if not vector_storage or not vector_storage.connected:
            return {
                "success": True,
                "status": "vector_storage_not_initialized",
                "documents_count": 0,
                "vectors_count": 0,
                "collections": []
            }

        collection_info = vector_storage.get_collection_info()

        # 获取文档列表以统计实际文档数量
        documents = vector_storage.list_all_documents()
        documents_count = len(documents)

        return {
            "success": True,
            "status": "healthy",
            "collection_name": "documents",
            "documents_count": documents_count,
            "vectors_count": collection_info.get("points_count", 0)
        }

    except Exception as e:
        logger.error(f"获取文档状态失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"获取文档状态失败: {str(e)}"
        )


@router.get("/list")
async def get_documents_list():
    """
    获取知识库中的所有文档列表

    返回每个文档的详细信息，包括文件名、入库日期、分块数量等
    """
    try:
        vector_storage = get_vector_storage()

        if not vector_storage or not vector_storage.connected:
            return {
                "success": True,
                "data": [],
                "message": "向量数据库未连接"
            }

        # 获取文档列表
        documents = vector_storage.list_all_documents()

        return {
            "success": True,
            "data": documents,
            "count": len(documents)
        }

    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"获取文档列表失败: {str(e)}"
        )


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """
    删除指定文档

    根据 doc_id 删除文档及其所有关联的分块
    """
    try:
        vector_storage = get_vector_storage()

        if not vector_storage or not vector_storage.connected:
            raise HTTPException(
                status_code=500,
                detail="向量数据库未连接"
            )

        # 删除文档
        result = vector_storage.delete_document(doc_id)

        if result.get("success"):
            return {
                "success": True,
                "message": f"文档已删除，共清理 {result.get('deleted_chunks', 0)} 个分块"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "删除文档失败")
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"删除文档失败: {str(e)}"
        )


@router.get("")
async def get_documents():
    """
    获取文档列表（已弃用，请使用 /api/documents/list）

    返回向量数据库中的所有文档列表
    """
    # 重定向到新的列表接口
    return await get_documents_list()

# vector_storage.py
"""
向量存储管理 - 使用Qdrant
"""

import logging
import hashlib
import time
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from config import VectorConfig

logger = logging.getLogger(__name__)

class VectorStorage:
    """向量存储管理器"""
    
    def __init__(self):
        self.config = VectorConfig.from_env()
        self.client = None
        self.connected = False
        self.collection_ready = False
        self._connect_failed = False  # 标记连接是否已失败过
        
    def connect(self, retry_count: int = 2, timeout: int = 5) -> bool:
        """连接向量数据库

        Args:
            retry_count: 重试次数，默认减少到2次以加快启动速度
            timeout: 连接超时时间（秒），默认5秒
        """
        # 如果已经连接失败过，跳过重试
        if self._connect_failed:
            return False

        for attempt in range(retry_count):
            try:
                logger.info(f"尝试连接Qdrant ({attempt+1}/{retry_count})...")

                self.client = QdrantClient(
                    host=self.config.qdrant_host,
                    port=self.config.qdrant_port,
                    timeout=timeout,  # 减少超时时间
                    grpc_port=self.config.qdrant_port + 1,
                    prefer_grpc=False
                )

                # 测试连接
                collections = self.client.get_collections()
                self.connected = True

                # 确保集合存在
                if not self._ensure_collection():
                    logger.warning("集合创建或验证失败")
                    continue

                logger.info(f"✅ 已连接到Qdrant: {self.config.qdrant_host}:{self.config.qdrant_port}")
                logger.info(f"可用集合: {[col.name for col in collections.collections]}")

                return True

            except Exception as e:
                logger.error(f"❌ 连接Qdrant失败 (尝试{attempt+1}): {e}")
                if attempt < retry_count - 1:
                    time.sleep(1)  # 减少等待时间

        # 标记连接失败，避免后续重复尝试
        self._connect_failed = True
        self.connected = False
        logger.warning("⚠️  Qdrant连接失败，向量搜索功能将被禁用")
        return False
    
    def _ensure_collection(self) -> bool:
        """确保集合存在并配置正确"""
        try:
            collections = self.client.get_collections()
            collection_names = [col.name for col in collections.collections]

            # 检查集合是否存在
            if self.config.collection_name in collection_names:
                # 集合已存在，直接标记为就绪，跳过验证
                self.collection_ready = True
                logger.info(f"✅ 集合已存在: {self.config.collection_name}")
                return True
            else:
                # 创建新集合
                logger.info(f"创建新的Qdrant集合: {self.config.collection_name}")

                self.client.create_collection(
                    collection_name=self.config.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.config.embedding_dimension,
                        distance=models.Distance.COSINE
                    )
                )

                self.collection_ready = True
                logger.info(f"✅ 集合创建成功: {self.config.collection_name}")
                return True
                
        except Exception as e:
            logger.error(f"❌ 确保集合存在失败: {e}")
            self.collection_ready = False
            return False
    
    def store_document(self, doc_id: str, chunks: List[str], 
                       embeddings: List[List[float]], 
                       metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        存储文档到向量数据库
        
        Args:
            doc_id: 文档ID
            chunks: 文本分块列表
            embeddings: 对应的嵌入向量列表
            metadata: 元数据
            
        Returns:
            存储结果
        """
        if not self.connected and not self.connect():
            return {"success": False, "error": "无法连接Qdrant"}
        
        if len(chunks) != len(embeddings):
            return {"success": False, "error": "分块数量和嵌入数量不匹配"}
        
        if not chunks:
            return {"success": False, "error": "没有分块可存储"}
        
        try:
            points = []
            stored_count = 0
            
            for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                try:
                    # 生成唯一ID (使用UUID的字符串形式)
                    point_id = str(uuid.uuid4())

                    # 创建点数据
                    point = models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "doc_id": doc_id,
                            "chunk_index": i,
                            "text": chunk_text,
                            "chunk_text": chunk_text,  # 兼容字段
                            "metadata": metadata,
                            "filename": metadata.get("filename", "unknown"),
                            "mime_type": metadata.get("mime_type", ""),
                            "ingested_at": metadata.get("ingested_at", ""),
                            "total_chunks": len(chunks)
                        }
                    )
                    points.append(point)
                    stored_count += 1

                except Exception as e:
                    logger.error(f"❌ 准备分块 {i} 失败: {e}")
                    continue
            
            # 批量插入
            if points:
                self.client.upsert(
                    collection_name=self.config.collection_name,
                    points=points,
                    wait=True
                )
                
                logger.debug(f"✅ 已存储文档 {doc_id}, 成功分块数: {stored_count}/{len(chunks)}")
                
                return {
                    "success": True,
                    "doc_id": doc_id,
                    "stored_chunks": stored_count,
                    "total_chunks": len(chunks),
                    "failed_chunks": len(chunks) - stored_count
                }
            else:
                return {"success": False, "error": "没有有效的点可存储"}
            
        except Exception as e:
            logger.error(f"❌ 存储文档失败: {e}")
            return {"success": False, "error": str(e)}
    
    def search(self, query_vector: List[float], top_k: int = 10,
               score_threshold: float = 0.3, 
               filter_by: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        向量搜索
        
        Args:
            query_vector: 查询向量
            top_k: 返回结果数量
            score_threshold: 分数阈值
            filter_by: 过滤条件
            
        Returns:
            搜索结果列表
        """
        if not self.connected and not self.connect():
            return []
        
        try:
            # 构建过滤条件
            search_filter = None
            if filter_by:
                must_conditions = []
                for key, value in filter_by.items():
                    if isinstance(value, list):
                        must_conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchAny(any=value)
                            )
                        )
                    else:
                        must_conditions.append(
                            models.FieldCondition(
                                key=key,
                                match=models.MatchValue(value=value)
                            )
                        )
                
                if must_conditions:
                    search_filter = models.Filter(must=must_conditions)
            
            # 执行搜索 - 使用新版 API (query_points)
            logger.debug(f"🔍 Qdrant query调用: collection={self.config.collection_name}, vector_dim={len(query_vector)}, limit={top_k}")

            search_results = self.client.query_points(
                collection_name=self.config.collection_name,
                query=query_vector,
                limit=top_k,
                with_payload=True
            )

            # query_points 返回的是 QueryResponse 对象，需要访问 .points 属性
            points = search_results.points if hasattr(search_results, 'points') else []

            logger.debug(f"📋 Qdrant返回 {len(points)} 个原始结果")

            # 格式化结果
            formatted_results = []
            for result in points:
                payload = result.payload or {}

                # 构建结果
                formatted_result = {
                    "id": str(result.id),
                    "score": float(result.score),
                    "text": payload.get("text", payload.get("chunk_text", "")),
                    "metadata": payload.get("metadata", {}),
                    "chunk_index": payload.get("chunk_index"),
                    "doc_id": payload.get("doc_id"),
                    "source_document": payload.get("filename", "unknown")
                }

                formatted_results.append(formatted_result)

            logger.debug(f"✅ 搜索完成，找到 {len(formatted_results)} 个结果")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ 搜索失败: {e}")
            return []
    
    def delete_document(self, doc_id: str) -> Dict[str, Any]:
        """删除文档"""
        if not self.connected and not self.connect():
            return {"success": False, "error": "无法连接Qdrant"}
        
        try:
            # 先统计要删除的点数
            search_results = self.client.scroll(
                collection_name=self.config.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="doc_id",
                            match=models.MatchValue(value=doc_id)
                        )
                    ]
                ),
                limit=1,
                with_payload=False
            )
            
            total_points = len(search_results[0])
            
            # 执行删除
            self.client.delete(
                collection_name=self.config.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="doc_id",
                                match=models.MatchValue(value=doc_id)
                            )
                        ]
                    )
                )
            )
            
            logger.info(f"✅ 已删除文档: {doc_id}, 删除点数: {total_points}")
            return {
                "success": True,
                "doc_id": doc_id,
                "deleted_points": total_points,
                "message": f"文档已删除，共{total_points}个分块"
            }
            
        except Exception as e:
            logger.error(f"❌ 删除文档失败: {e}")
            return {"success": False, "error": str(e)}
    
    def clear_collection(self) -> Dict[str, Any]:
        """清空集合"""
        try:
            # 先获取集合信息，但只提取我们需要的字段
            try:
                collection_info = self.client.get_collection(self.config.collection_name)
                points_count = collection_info.points_count if hasattr(collection_info, 'points_count') else 0
            except Exception:
                points_count = 0

            # 删除集合
            self.client.delete_collection(collection_name=self.config.collection_name)

            # 重新创建集合
            time.sleep(1)
            self._ensure_collection()

            logger.info(f"✅ 已清空集合: {self.config.collection_name}, 清理点数: {points_count}")

            # 只返回简单的数据类型，不返回任何Qdrant对象
            return {
                "success": True,
                "cleared_points": int(points_count) if points_count is not None else 0,
                "message": f"集合已清空，共清理{points_count}个点"
            }

        except Exception as e:
            logger.error(f"❌ 清空集合失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息（仅返回必要字段，避免前端解析错误）"""
        if not self.connected and not self.connect():
            return {"connected": False}

        try:
            collection_info = self.client.get_collection(self.config.collection_name)

            # 只返回必要的字段，不返回完整的Qdrant配置对象
            points_count = collection_info.points_count if hasattr(collection_info, 'points_count') else 0
            status = str(collection_info.status) if hasattr(collection_info, 'status') else "unknown"

            return {
                "connected": True,
                "collection_name": self.config.collection_name,
                "points_count": points_count,
                "status": status
            }
        except Exception as e:
            logger.error(f"❌ 获取集合信息失败: {e}")
            return {"connected": False, "error": str(e)}
    
    def chunk_text(self, text: str, chunk_size: int = None, 
                   chunk_overlap: int = None) -> List[str]:
        """
        文本分块
        
        Args:
            text: 输入文本
            chunk_size: 块大小
            chunk_overlap: 重叠大小
            
        Returns:
            文本块列表
        """
        chunk_size = chunk_size or self.config.chunk_size
        chunk_overlap = chunk_overlap or self.config.chunk_overlap
        
        if not text or len(text.strip()) == 0:
            return []
        
        # 简单分块算法
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            # 计算结束位置
            end = start + chunk_size
            
            if end >= text_length:
                chunks.append(text[start:])
                break
            
            # 查找合适的分割点
            split_positions = []
            
            # 优先在段落边界分割
            for delimiter in ['\n\n', '\n', '。', '！', '？', '.', '!', '?', ';', '；']:
                pos = text.rfind(delimiter, start, end)
                if pos != -1:
                    split_positions.append(pos + len(delimiter))
            
            # 其次在句子边界分割
            for delimiter in ['，', ',', '、', ' ']:
                pos = text.rfind(delimiter, start, end)
                if pos != -1:
                    split_positions.append(pos + len(delimiter))
            
            # 选择最佳分割点
            if split_positions:
                end = max(split_positions)
            
            chunks.append(text[start:end].strip())
            
            # 更新起始位置，考虑重叠
            start = end - chunk_overlap if chunk_overlap > 0 else end
        
        # 过滤空块
        chunks = [chunk for chunk in chunks if chunk.strip()]
        
        return chunks
    
    def list_all_documents(self) -> List[Dict[str, Any]]:
        """
        列出所有文档及其元数据

        Returns:
            文档列表，每个文档包含 filename, ingested_at, chunk_count 等信息
        """
        if not self.connected and not self.connect():
            return []

        try:
            # 使用 scroll 获取所有点
            all_points = []
            offset = None

            while True:
                records, offset = self.client.scroll(
                    collection_name=self.config.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )

                if not records:
                    break

                all_points.extend(records)

                if offset is None:
                    break

            # 按 doc_id 分组
            documents = {}
            for record in all_points:
                payload = record.payload or {}
                doc_id = payload.get("doc_id")

                if not doc_id:
                    continue

                # 如果这个文档还没有记录，创建一个
                if doc_id not in documents:
                    documents[doc_id] = {
                        "doc_id": doc_id,
                        "filename": payload.get("filename", "unknown"),
                        "mime_type": payload.get("mime_type", ""),
                        "ingested_at": payload.get("ingested_at", ""),
                        "chunk_count": 0,
                        "metadata": payload.get("metadata", {})
                    }

                # 增加分块计数
                documents[doc_id]["chunk_count"] += 1

            # 转换为列表并排序
            doc_list = list(documents.values())
            # 按入库时间倒序排列
            doc_list.sort(key=lambda x: x.get("ingested_at", ""), reverse=True)

            logger.info(f"✅ 获取到 {len(doc_list)} 个文档")
            return doc_list

        except Exception as e:
            logger.error(f"❌ 列出文档失败: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            connected = self.connect()
            if not connected:
                return {"status": "unhealthy", "connected": False}

            # 检查集合
            collection_info = self.get_collection_info()

            return {
                "status": "healthy" if collection_info.get("connected") else "degraded",
                "connected": connected,
                "collection_ready": self.collection_ready,
                "collection_info": collection_info
            }
        except Exception as e:
            return {"status": "unhealthy", "connected": False, "error": str(e)}


# 全局单例
_qdrant_client_instance = None

def get_qdrant_client() -> Optional[QdrantClient]:
    """
    获取全局 Qdrant 客户端实例

    Returns:
        QdrantClient: Qdrant 客户端实例，如果未初始化则返回 None
    """
    global _qdrant_client_instance

    if _qdrant_client_instance is None:
        try:
            config = VectorConfig.from_env()
            _qdrant_client_instance = QdrantClient(
                host=config.qdrant_host,
                port=config.qdrant_port,
                timeout=60,
                grpc_port=config.qdrant_port + 1,
                prefer_grpc=False
            )
            logger.info("✅ 全局 Qdrant 客户端已创建")
        except Exception as e:
            logger.error(f"❌ 创建 Qdrant 客户端失败: {e}")
            return None

    return _qdrant_client_instance

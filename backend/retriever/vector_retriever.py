# retriever/vector_retriever.py
"""
向量检索器
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional

from core.schemas import SearchQuery, SearchResult, DocumentChunk
from retriever.embedding_model import EmbeddingModel
from storage.qdrant_client import QdrantStorage
from config import config

logger = logging.getLogger(__name__)

class VectorRetriever:
    """向量检索器"""
    
    def __init__(self, embedding_model: EmbeddingModel, vector_store: QdrantStorage):
        self.embedding_model = embedding_model
        self.vector_store = vector_store
    
    def search(self, query: SearchQuery) -> List[SearchResult]:
        """执行向量搜索"""
        try:
            # 向量化查询
            query_vector = self.embedding_model.embed_text(query.query)
            
            # 执行向量搜索
            results = self.vector_store.search(
                query_vector=query_vector,
                top_k=query.top_k,
                filters=query.filters
            )
            
            # 应用分数阈值
            if query.score_threshold:
                results = [r for r in results if r.score >= query.score_threshold]
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 搜索失败: {e}")
            return []
    
    def prepare_document_chunks(self, text: str, metadata: Dict[str, Any], 
                                chunk_size: int = None, chunk_overlap: int = None) -> List[DocumentChunk]:
        """准备文档分块"""
        chunk_size = chunk_size or config.vector.chunk_size
        chunk_overlap = chunk_overlap or config.vector.chunk_overlap
        
        # 简单文本分割（避免依赖复杂的text splitter）
        chunks = self._simple_text_split(text, chunk_size, chunk_overlap)
        
        doc_chunks = []
        for i, chunk_text in enumerate(chunks):
            # 生成唯一ID
            content_hash = hashlib.md5(chunk_text.encode()).hexdigest()[:16]
            chunk_id = f"{metadata.get('doc_id', 'unk')}_{i}_{content_hash}"
            
            doc_chunk = DocumentChunk(
                id=chunk_id,
                text=chunk_text,
                metadata=metadata,
                chunk_index=i,
                page_number=metadata.get('page_number')
            )
            doc_chunks.append(doc_chunk)
        
        return doc_chunks
    
    def _simple_text_split(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """简单文本分割器"""
        if not text:
            return []
        
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            # 计算当前块的结束位置
            end = start + chunk_size
            
            # 如果剩余文本不足一个块，直接取完
            if end >= text_length:
                chunks.append(text[start:])
                break
            
            # 尝试在句子边界处分割
            split_positions = []
            
            # 查找句子结束符
            for delimiter in ['\n\n', '\n', '。', '！', '？', '.', '!', '?']:
                pos = text.rfind(delimiter, start, end)
                if pos != -1:
                    split_positions.append(pos + len(delimiter))
            
            # 查找逗号或空格
            for delimiter in ['；', ';', '，', ',', ' ']:
                pos = text.rfind(delimiter, start, end)
                if pos != -1:
                    split_positions.append(pos + len(delimiter))
            
            # 选择最合适的分割位置
            if split_positions:
                end = max(split_positions)
            else:
                # 没有找到合适的分割点，强制在块大小处分隔
                end = start + chunk_size
            
            chunks.append(text[start:end].strip())
            
            # 移动起始位置，考虑重叠
            start = end - chunk_overlap
        
        # 过滤空块
        chunks = [chunk for chunk in chunks if chunk.strip()]
        
        return chunks
    
    def embed_and_store_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """嵌入分块并存储到向量数据库"""
        if not chunks:
            return False
        
        try:
            # 批量嵌入
            texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_model.embed_batch(texts)
            
            # 为每个分块设置嵌入
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
            
            # 存储到向量数据库
            success = self.vector_store.upsert_documents(chunks)
            
            return success
        except Exception as e:
            logger.error(f"❌ 嵌入和存储分块失败: {e}")
            return False
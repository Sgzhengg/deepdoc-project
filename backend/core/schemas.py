# core/schemas.py
"""
数据模型定义
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    """处理状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentChunk(BaseModel):
    """文档分块"""
    id: str
    text: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    page_number: Optional[int] = None
    chunk_index: int
    
    class Config:
        arbitrary_types_allowed = True

class SearchQuery(BaseModel):
    """搜索查询"""
    query: str
    top_k: int = Field(default=10, ge=1, le=100)
    score_threshold: Optional[float] = Field(default=None, ge=0, le=1)
    filters: Optional[Dict[str, Any]] = None

class SearchResult(BaseModel):
    """搜索结果"""
    text: str
    score: float = Field(ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None
    source_document: Optional[str] = None

class DocumentMetadata(BaseModel):
    """文档元数据"""
    filename: str
    file_size: int
    mime_type: str
    total_pages: int
    total_chunks: int
    processing_time: float
    status: ProcessingStatus = ProcessingStatus.COMPLETED
    uploaded_at: datetime = Field(default_factory=datetime.now)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)

class BatchUploadRequest(BaseModel):
    """批量上传请求"""
    file_paths: List[str]
    metadata: Optional[Dict[str, Any]] = None

class HealthCheck(BaseModel):
    """健康检查响应"""
    status: str
    deepdoctection: bool
    qdrant: bool
    redis: bool
    embedding_model: bool
    timestamp: datetime

class IngestResponse(BaseModel):
    """文档入库响应"""
    doc_id: str
    filename: str
    total_chunks: int
    status: ProcessingStatus
    processing_time: float
    message: str
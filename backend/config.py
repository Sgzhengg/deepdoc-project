"""
配置管理 - 从环境变量加载配置
"""
import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class VectorConfig:
    """向量存储配置"""
    qdrant_host: str
    qdrant_port: int
    collection_name: str
    embedding_model: str
    embedding_dimension: int
    batch_size: int
    use_fp16: bool
    device: str
    chunk_size: int
    chunk_overlap: int

    @classmethod
    def from_env(cls) -> 'VectorConfig':
        """从环境变量加载配置"""
        return cls(
            qdrant_host=os.getenv("QDRANT_HOST", "localhost"),
            qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
            collection_name=os.getenv("QDRANT_COLLECTION", "documents"),
            embedding_model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5"),
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1024")),
            batch_size=int(os.getenv("BATCH_SIZE", "256")),
            use_fp16=os.getenv("USE_FP16", "true").lower() == "true",
            device=os.getenv("DEVICE", "cuda"),
            chunk_size=int(os.getenv("CHUNK_SIZE", "2000")),  # 增加到2000，保留更完整的上下文
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "200"))
        )

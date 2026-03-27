# retriever/embedding_model.py
"""
文本嵌入模型
"""

import logging
import os
from typing import List
from sentence_transformers import SentenceTransformer

from config import VectorConfig

logger = logging.getLogger(__name__)

class EmbeddingModel:
    """文本嵌入模型"""

    def __init__(self, model_name: str = None):
        config = VectorConfig.from_env()
        self.model_name = model_name or config.embedding_model
        self.model = None
        self.dimension = config.embedding_dimension

    def load(self) -> bool:
        """加载模型"""
        if self.model is None:
            try:
                logger.info(f"正在加载嵌入模型: {self.model_name}")

                # 检查是否强制使用 CPU
                use_cpu = os.getenv("EMBEDDING_USE_CPU", "false").lower() == "true"
                device = "cpu" if use_cpu else None

                if use_cpu:
                    logger.info("⚙️ 嵌入模型配置为使用 CPU")
                else:
                    logger.info("⚙️ 嵌入模型自动检测设备")

                # 离线模式，使用本地缓存
                os.environ['HF_HUB_OFFLINE'] = '1'
                os.environ['TRANSFORMERS_OFFLINE'] = '1'

                self.model = SentenceTransformer(self.model_name, device=device)

                # 测试维度
                test_embedding = self.model.encode(["test"])
                actual_dimension = len(test_embedding[0])

                if actual_dimension != self.dimension:
                    logger.warning(f"模型维度不匹配: 配置={self.dimension}, 实际={actual_dimension}")
                    self.dimension = actual_dimension

                logger.info(f"✅ 嵌入模型加载完成，维度: {self.dimension}")
                return True

            except Exception as e:
                logger.error(f"❌ 加载嵌入模型失败: {e}")
                return False
        return True
    
    def embed_text(self, text: str) -> List[float]:
        """嵌入单个文本"""
        if not self.model and not self.load():
            raise RuntimeError("无法加载嵌入模型")
        
        embedding = self.model.encode([text])[0]
        return embedding.tolist()
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文本"""
        if not self.model and not self.load():
            raise RuntimeError("无法加载嵌入模型")
        
        embeddings = self.model.encode(texts)
        return [emb.tolist() for emb in embeddings]
    
    def get_dimension(self) -> int:
        """获取嵌入维度"""
        if not self.model and not self.load():
            return self.dimension
        return self.dimension
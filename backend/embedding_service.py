# embedding_service.py
"""
文本嵌入服务 - 使用BAAI/bge-m3模型
"""

import os
import logging
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import torch

from config import VectorConfig

logger = logging.getLogger(__name__)

class EmbeddingService:
    """文本嵌入服务 - 使用高质量开源模型"""
    
    def __init__(self, model_name: str = None):
        self.config = VectorConfig.from_env()

        # 模型选择优先级：参数 > 配置 > 默认
        # 强制使用512维模型以匹配Qdrant集合配置
        self.model_name = model_name or self.config.embedding_model or "BAAI/bge-small-zh-v1.5"

        # 根据显存和集合配置自动选择模型
        if self._should_use_light_model():
            self.model_name = "BAAI/bge-small-zh-v1.5"
            logger.info(f"显存有限，自动切换到轻量模型: {self.model_name}")

        self.model = None
        self.device = self._get_device()

        # RTX 4090 性能优化
        self.batch_size = int(os.getenv("BATCH_SIZE", "128"))  # 从环境变量读取
        self.use_fp16 = os.getenv("USE_FP16", "True").lower() == "true"

        # 模型信息
        self.model_info = {
            "name": self.model_name,
            "dimension": self._get_model_dimension(),
            "device": self.device,
            "batch_size": self.batch_size,
            "use_fp16": self.use_fp16
        }
    
    def _get_device(self) -> str:
        """获取运行设备"""
        # 检查环境变量是否强制使用 CPU
        use_cpu = os.getenv("EMBEDDING_USE_CPU", "false").lower() == "true"

        if use_cpu:
            logger.info("⚙️ 嵌入模型配置为使用 CPU")
            return "cpu"

        if torch.cuda.is_available():
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            logger.info(f"GPU可用: {torch.cuda.get_device_name(0)}, 显存: {gpu_memory:.1f}GB")
            return "cuda"
        else:
            logger.warning("GPU不可用，将使用CPU（速度会慢很多）")
            return "cpu"
    
    def _should_use_light_model(self) -> bool:
        """判断是否应该使用轻量模型"""
        if torch.cuda.is_available():
            # 检查显存大小
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            
            # 如果显存小于8GB，使用轻量模型
            if gpu_memory < 8:
                return True
            
            # bge-m3需要较大显存
            if "bge-m3" in self.model_name.lower() and gpu_memory < 12:
                return True
        
        return False
    
    def _get_model_dimension(self) -> int:
        """获取模型维度"""
        # 常见模型的维度
        model_dimensions = {
            "bge-m3": 1024,
            "bge-large-zh": 1024,
            "bge-large-zh-v1.5": 1024,
            "bge-small-zh-v1.5": 512,
            "paraphrase-multilingual-minilm": 384,
            "minilm": 384
        }
        
        model_name_lower = self.model_name.lower()
        for key, dim in model_dimensions.items():
            if key in model_name_lower:
                return dim
        
        # 默认维度
        return 1024
    
    def load_model(self) -> bool:
        """加载模型"""
        if self.model is not None:
            return True

        try:
            logger.info(f"正在加载嵌入模型: {self.model_name}")
            logger.info(f"模型信息: {self.model_info}")

            # 设置环境变量以使用镜像
            os.environ['HF_HUB_OFFLINE'] = '1'  # 离线模式，使用本地缓存
            os.environ['TRANSFORMERS_OFFLINE'] = '1'

            # 加载模型 - sentence-transformers 2.7+ 兼容
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=os.path.expanduser('~/.cache/huggingface/hub')
            )

            # 启用混合精度（FP16）以提升 RTX 4090 性能
            if self.use_fp16 and self.device == "cuda":
                try:
                    import torch
                    if torch.cuda.is_bf16_supported():
                        self.model.half()
                        logger.info("✅ 启用 FP16 混合精度（RTX 4090 优化）")
                    else:
                        self.model.half()
                        logger.info("✅ 启用 FP16 混合精度")
                except Exception as e:
                    logger.warning(f"无法启用混合精度: {e}")

            # 测试模型
            test_embedding = self.model.encode(["测试文本"])
            actual_dimension = test_embedding.shape[1]

            # 更新模型信息
            self.model_info.update({
                "actual_dimension": actual_dimension,
                "loaded": True,
                "max_seq_length": self.model.max_seq_length
            })

            logger.info(f"✅ 嵌入模型加载完成")
            logger.info(f"   模型: {self.model_name}")
            logger.info(f"   维度: {actual_dimension}")
            logger.info(f"   设备: {self.device}")
            logger.info(f"   最大序列长度: {self.model.max_seq_length}")
            logger.info(f"   批处理大小: {self.batch_size}")
            if self.use_fp16:
                logger.info(f"   混合精度: 已启用")

            return True

        except Exception as e:
            logger.error(f"❌ 加载嵌入模型失败: {e}")

            # 尝试回退到轻量模型
            if self.model_name != "BAAI/bge-small-zh-v1.5":
                logger.info("尝试回退到轻量模型...")
                self.model_name = "BAAI/bge-small-zh-v1.5"
                return self.load_model()

            return False
    
    def embed_text(self, text: str, normalize: bool = True) -> List[float]:
        """
        嵌入单个文本
        
        Args:
            text: 输入文本
            normalize: 是否归一化向量（推荐True，提高检索效果）
            
        Returns:
            嵌入向量
        """
        if not self.model and not self.load_model():
            raise RuntimeError("无法加载嵌入模型")
        
        try:
            # 编码文本
            embedding = self.model.encode(
                [text],
                normalize_embeddings=normalize,
                show_progress_bar=False
            )[0]
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"❌ 文本嵌入失败: {e}")
            raise
    
    def embed_batch(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        """
        批量嵌入文本
        
        Args:
            texts: 文本列表
            normalize: 是否归一化向量
            
        Returns:
            嵌入向量列表
        """
        if not self.model and not self.load_model():
            raise RuntimeError("无法加载嵌入模型")
        
        if not texts:
            return []
        
        try:
            # 批量编码 - 使用优化的批处理大小
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=normalize,
                show_progress_bar=True if len(texts) > 10 else False,
                batch_size=self.batch_size  # RTX 4090 优化的批处理大小
            )

            return [emb.tolist() for emb in embeddings]
            
        except Exception as e:
            logger.error(f"❌ 批量文本嵌入失败: {e}")
            raise
    
    def get_embeddings_dimension(self) -> int:
        """获取嵌入维度"""
        return self.model_info.get("actual_dimension", self.model_info["dimension"])
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model": self.model_info,
            "status": {
                "loaded": self.model is not None,
                "device": self.device,
                "cuda_available": torch.cuda.is_available()
            }
        }
    
    def get_supported_models(self) -> List[Dict[str, Any]]:
        """获取支持的模型列表"""
        return [
            {
                "name": "BAAI/bge-m3",
                "dimension": 1024,
                "language": ["zh", "en", "multi"],
                "description": "目前最好的多语言模型之一，支持中文",
                "recommended": True,
                "memory_required": ">=12GB GPU"
            },
            {
                "name": "BAAI/bge-large-zh-v1.5",
                "dimension": 1024,
                "language": ["zh"],
                "description": "专门为中文优化的模型",
                "recommended": True,
                "memory_required": ">=8GB GPU"
            },
            {
                "name": "BAAI/bge-small-zh-v1.5",
                "dimension": 512,
                "language": ["zh"],
                "description": "轻量级中文模型，适合资源有限的环境",
                "recommended": False,
                "memory_required": ">=2GB GPU"
            },
            {
                "name": "paraphrase-multilingual-MiniLM-L12-v2",
                "dimension": 384,
                "language": ["multi"],
                "description": "轻量级多语言模型",
                "recommended": False,
                "memory_required": ">=2GB GPU"
            }
        ]
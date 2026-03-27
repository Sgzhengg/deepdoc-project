"""
清空向量数据库 - 通用方案
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def clear_vector_database():
    """清空向量数据库中的旧数据"""
    print("=" * 80)
    print("清空向量数据库")
    print("=" * 80)

    try:
        from qdrant_client import QdrantClient
        from config import VectorConfig
        import logging

        logging.basicConfig(level=logging.INFO)

        print("\n[步骤1] 连接Qdrant")
        print("-" * 80)

        config = VectorConfig.from_env()
        client = QdrantClient(
            host=config.qdrant_host,
            port=config.qdrant_port,
            timeout=10
        )

        # 检查现有collections
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]
        print(f"现有collections: {collection_names}")

        # 删除documents collection
        if "documents" in collection_names:
            print("\n[步骤2] 删除旧的documents collection")
            print("-" * 80)

            client.delete_collection("documents")
            print("[OK] 已删除旧的documents collection")

            print("\n[步骤3] 创建新的空collection")
            print("-" * 80)

            from qdrant_client.http import models

            client.create_collection(
                collection_name="documents",
                vectors_config=models.VectorParams(
                    size=512,
                    distance=models.Distance.COSINE
                )
            )
            print("[OK] 已创建新的空collection")

            print("\n" + "=" * 80)
            print("[完成] 向量数据库已清空")
            print("=" * 80)
            print("\n下一步：请重新上传文档，系统将使用新的表格解析逻辑")
        else:
            print("\n[INFO] documents collection不存在，无需清空")

    except Exception as e:
        print(f"\n[错误] 操作失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    clear_vector_database()

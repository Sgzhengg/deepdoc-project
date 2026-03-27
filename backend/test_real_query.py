"""
完整测试：模拟真实查询流程
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_complete_query():
    """测试完整的查询流程"""
    print("=" * 80)
    print("完整查询流程测试")
    print("=" * 80)

    # 1. 测试表格查询（已修复）
    print("\n[步骤1] 表格查询测试")
    print("-" * 80)

    from agents.enhanced_table_analyzer import ChannelTableAnalyzer

    analyzer = ChannelTableAnalyzer()
    query = "59元潮玩青春卡套餐包含哪些内容？"

    results = analyzer.query(query)

    if results:
        result = results[0]
        # 去除emoji
        answer = result.answer.replace('⭐', '').replace('【', '[').replace('】', ']')

        print(f"表格查询结果:\n{answer[:400]}")

        # 检查字段
        if '[套内通用流量' in answer and '10G' in answer:
            print("\n[OK] 表格数据正确: 套内通用流量 = 10G")
        else:
            print("\n[ERROR] 表格数据有问题")

    # 2. 检查向量数据库
    print("\n[步骤2] 向量数据库检查")
    print("-" * 80)

    try:
        from vector_storage import VectorStorage
        from qdrant_client import QdrantClient
        from config import VectorConfig

        config = VectorConfig.from_env()
        client = QdrantClient(
            host=config.qdrant_host,
            port=config.qdrant_port,
            timeout=5
        )

        # 检查collection
        collections = client.get_collections().collections
        print(f"Qdrant collections: {[c.name for c in collections]}")

        # 查询向量数据库
        from embedding_service import EmbeddingService
        embed_service = EmbeddingService()

        query_vector = embed_service.embed_text(query)

        search_result = client.search(
            collection_name="documents",
            query_vector=query_vector,
            limit=3,
            score_threshold=0.3
        )

        print(f"\n向量检索找到 {len(search_result)} 个结果")

        for i, hit in enumerate(search_result[:2], 1):
            print(f"\n结果 {i} (得分: {hit.score:.2f}):")
            if hasattr(hit, 'payload'):
                print(f"  来源: {hit.payload.get('source', 'N/A')}")
            if hasattr(hit, 'document'):
                doc = hit.document
                print(f"  内容: {doc[:150]}...")

    except Exception as e:
        print(f"向量数据库测试失败: {e}")

    # 3. 检查是否有缓存或索引需要更新
    print("\n[步骤3] 数据源一致性检查")
    print("-" * 80)

    # 检查表格缓存
    import json
    with open('agents/.tables_cache.json', 'r', encoding='utf-8') as f:
        tables = json.load(f)

    print(f"表格缓存版本: {tables.get('version', 'N/A')}")
    print(f"表格数量: {tables.get('tables_count', len(tables.get('tables', [])))}")

    # 检查59元潮玩青春卡数据
    for table in tables['tables']:
        if table['index'] == 0:
            for row in table['data']:
                if '59元潮玩青春卡' in str(row[0]):
                    print(f"\n表格缓存中的59元潮玩青春卡:")
                    print(f"  套内通用流量: {row[3]}")
                    print(f"  套内定向流量: {row[4]}")
                    break
            break

    print("\n" + "=" * 80)
    print("[结论] 问题分析")
    print("=" * 80)
    print("""
表格缓存数据正确：套内通用流量 = 10G，套内定向流量 = 30G

但AI回答错误（套内通用流量 = 30G），可能原因：
1. 向量数据库中存储的是旧数据（修复前索引的）
2. 需要重新索引文档到向量数据库

建议解决方案：
- 重新运行文档索引脚本，更新向量数据库
- 或者在文档中添加明确的标注，帮助AI区分
    """)

if __name__ == "__main__":
    try:
        test_complete_query()
    except Exception as e:
        print(f"\n[错误] {e}")
        import traceback
        traceback.print_exc()

"""
测试去硬编码后的表格查询功能
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from agents.enhanced_table_analyzer import ChannelTableAnalyzer

def test_similar_fields_detection():
    """测试相似字段检测功能"""
    print("=" * 80)
    print("测试：相似字段检测（通用算法）")
    print("=" * 80)

    analyzer = ChannelTableAnalyzer()

    # 测试表格0的表头
    test_headers = [
        '套餐名称',
        '方案ID',
        '套内通话\n（单位：分钟）',
        '套内通用流量\n（单位：GB）',
        '套内定向流量',
        '套外语音',
        '套外流量'
    ]

    print("\n测试表头:")
    for i, h in enumerate(test_headers):
        print(f"  列{i}: {h}")

    # 检测相似字段
    similar_groups = analyzer._detect_similar_fields(test_headers)

    print(f"\n检测到 {len(similar_groups)} 个相似字段组:")

    for group in similar_groups:
        print(f"\n  组名: {group['name']}")
        print(f"  成员: {group['members']}")

def test_table_query():
    """测试表格查询功能"""
    print("\n" + "=" * 80)
    print("测试：表格查询（去硬编码）")
    print("=" * 80)

    analyzer = ChannelTableAnalyzer()

    query = "59元潮玩青春卡套餐包含哪些内容？"
    print(f"\n查询问题：{query}")

    results = analyzer.query(query)

    if results:
        print(f"\n找到 {len(results)} 个相关结果")

        # 显示第一个结果
        result = results[0]
        print(f"\n答案（置信度: {result.confidence:.2f}）:")
        print("-" * 80)

        # 去除emoji，避免编码问题
        answer = result.answer.replace('⭐', '').replace('【', '[').replace('】', ']')
        print(answer[:500])

        print("-" * 80)

        # 验证关键字段
        print("\n验证关键字段:")
        if '[套内通用流量' in answer and '10G' in answer:
            print("  [OK] 正确: 套内通用流量 = 10G")
        if '[套内定向流量' in answer and '30G' in answer:
            print("  [OK] 正确: 套内定向流量 = 30G")

        # 检查是否有混淆
        if '30G通用' in answer:
            print("  [ERROR] 存在混淆: 30G通用流量")
        else:
            print("  [OK] 没有混淆通用和定向流量")
    else:
        print("未找到相关结果")

if __name__ == "__main__":
    try:
        test_similar_fields_detection()
        test_table_query()

        print("\n" + "=" * 80)
        print("[完成] 测试完成")
        print("=" * 80)
    except Exception as e:
        print(f"\n[错误] 测试失败：{e}")
        import traceback
        traceback.print_exc()

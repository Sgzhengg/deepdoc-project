"""
测试修复后的表格查询
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from agents.enhanced_table_analyzer import ChannelTableAnalyzer

def test_fixed_table():
    """测试修复后的表格查询"""
    print("=" * 80)
    print("测试修复后的表格查询")
    print("=" * 80)

    # 初始化表格分析器（会自动加载修复后的缓存）
    analyzer = ChannelTableAnalyzer()

    # 查询59元潮玩青春卡
    query = "59元潮玩青春卡套餐包含哪些内容？"
    print(f"\n查询问题：{query}\n")

    results = analyzer.query(query)

    if results:
        print(f"找到 {len(results)} 个相关结果\n")

        for i, result in enumerate(results[:2], 1):  # 只显示前2个结果
            print("=" * 80)
            print(f"结果 {i} (置信度: {result.confidence:.2f})")
            print("=" * 80)
            print(f"\n{result.answer}\n")
            print(f"说明：{result.explanation}\n")

            # 检查是否正确区分了通用流量和定向流量
            answer_text = result.answer
            if '10GB通用' in answer_text or '10G通用' in answer_text:
                print("[验证] 正确包含10GB通用流量")
            if '30GB定向' in answer_text or '30G定向' in answer_text:
                print("[验证] 正确包含30GB定向流量")
            if '30GB通用' in answer_text or '30G通用' in answer_text:
                print("[警告] 仍然存在错误：30GB通用流量")
    else:
        print("未找到相关结果")

if __name__ == "__main__":
    try:
        test_fixed_table()
        print("\n" + "=" * 80)
        print("[完成] 测试完成")
        print("=" * 80)
    except Exception as e:
        print(f"\n[错误] 测试失败：{e}")
        import traceback
        traceback.print_exc()

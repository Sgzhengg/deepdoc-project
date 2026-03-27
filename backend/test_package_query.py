"""
测试套餐查询优化效果
验证表格数据呈现和流量字段区分是否正确
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from agents.enhanced_table_analyzer import ChannelTableAnalyzer
from services.post_processor import AnswerPostProcessor
from services.business_rules_clarifier import PACKAGE_59_PROMPT

def test_table_query():
    """测试表格查询功能"""
    print("=" * 80)
    print("测试：59元潮玩青春卡套餐查询")
    print("=" * 80)

    # 初始化表格分析器
    analyzer = ChannelTableAnalyzer()

    # 测试查询
    query = "59元潮玩青春卡套餐包含哪些内容？"
    print(f"\n[查询] 问题：{query}\n")

    # 执行查询
    results = analyzer.query(query)

    if results:
        print(f"[成功] 找到 {len(results)} 个相关表格\n")

        for i, result in enumerate(results, 1):
            print(f"{'=' * 80}")
            print(f"结果 {i} (置信度: {result.confidence:.2f})")
            print(f"{'=' * 80}")
            print(f"\n{result.answer}\n")
            print(f"说明：{result.explanation}")
            print()
    else:
        print("[失败] 未找到相关表格")

    # 测试后处理器
    print("\n" + "=" * 80)
    print("测试：答案后处理器")
    print("=" * 80)

    processor = AnswerPostProcessor()

    # 模拟AI生成的答案（包含错误的流量信息）
    test_answer_wrong = """【直接回答】
59元潮玩青春卡套餐包含30GB通用流量。

【详细说明】
根据表格数据，59元潮玩青春卡套餐包含30GB通用流量、全国亲情网服务等。

【数据来源】
12月放号独立部分（政策-操作-ID）.docx
"""

    print(f"\n[测试1] 错误答案：\n{test_answer_wrong}")
    corrected = processor._correct_flow_info(test_answer_wrong)
    print(f"\n[修正] 修正后：\n{corrected}")

    # 测试正确的答案
    test_answer_correct = """【直接回答】
59元潮玩青春卡套餐包含10GB通用流量、30GB定向流量。

【详细说明】
根据表格数据，59元潮玩青春卡套餐包含10GB通用流量、30GB定向流量、全国亲情网服务等。

【数据来源】
12月放号独立部分（政策-操作-ID）.docx
"""

    print(f"\n[测试2] 正确答案：\n{test_answer_correct}")
    corrected2 = processor._correct_flow_info(test_answer_correct)
    print(f"\n[验证] 修正后：\n{corrected2}")

    # 显示业务规则提示
    print("\n" + "=" * 80)
    print("业务规则提示（PACKAGE_59_PROMPT）")
    print("=" * 80)
    print(PACKAGE_59_PROMPT)

if __name__ == "__main__":
    try:
        test_table_query()
        print("\n" + "=" * 80)
        print("[完成] 测试完成")
        print("=" * 80)
    except Exception as e:
        print(f"\n[失败] 测试失败：{e}")
        import traceback
        traceback.print_exc()

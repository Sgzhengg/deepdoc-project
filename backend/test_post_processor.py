"""
测试后处理器的流量信息修正功能
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from services.post_processor import AnswerPostProcessor

def test_post_processor():
    """测试后处理器的流量信息修正功能"""
    print("=" * 80)
    print("测试：答案后处理器 - 流量信息修正")
    print("=" * 80)

    processor = AnswerPostProcessor()

    # 测试用例
    test_cases = [
        {
            "name": "错误答案：只说30GB通用流量（最常见错误）",
            "input": """【直接回答】
59元潮玩青春卡套餐包含30GB国内通用流量。

【详细说明】
根据表格数据，59元潮玩青春卡套餐包含30GB通用流量、全国亲情网服务。

【数据来源】
12月放号独立部分（政策-操作-ID）.docx
""",
            "expected": "应该修正为10GB通用流量"
        },
        {
            "name": "错误答案：通用流量：30GB",
            "input": """【直接回答】
59元潮玩青春卡套餐包含：
- 通用流量：30GB
- 定向流量：30GB

【详细说明】
套餐包含通用流量和定向流量各30GB。

【数据来源】
12月放号独立部分（政策-操作-ID）.docx
""",
            "expected": "应该修正为10GB通用流量"
        },
        {
            "name": "正确答案：10GB通用+30GB定向",
            "input": """【直接回答】
59元潮玩青春卡套餐包含10GB通用流量、30GB定向流量。

【详细说明】
根据表格数据，59元潮玩青春卡套餐包含10GB通用流量、30GB定向流量、全国亲情网服务。

【数据来源】
12月放号独立部分（政策-操作-ID）.docx
""",
            "expected": "应该保持不变"
        },
        {
            "name": "正确答案：通用10GB、定向30GB",
            "input": """【直接回答】
59元潮玩青春卡套餐内容：
- 国内通用流量：10GB
- 定向流量：30GB

【详细说明】
套餐包含10GB国内通用流量和30GB定向流量。

【数据来源】
12月放号独立部分（政策-操作-ID）.docx
""",
            "expected": "应该保持不变"
        },
        {
            "name": "错误答案：只提到30GB定向，缺少10GB通用",
            "input": """【直接回答】
59元潮玩青春卡套餐包含30GB定向流量。

【详细说明】
套餐包含30GB定向流量。

【数据来源】
12月放号独立部分（政策-操作-ID）.docx
""",
            "expected": "应该补充10GB通用流量"
        },
    ]

    print("\n")
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"测试用例 {i}: {test_case['name']}")
        print(f"{'=' * 80}")
        print(f"\n输入：\n{test_case['input']}")
        print(f"\n期望：{test_case['expected']}")

        # 执行修正
        corrected = processor._correct_flow_info(test_case['input'])

        print(f"\n输出：\n{corrected}")

        # 检查是否修正成功
        if "错误" in test_case['name']:
            if "10GB通用" in corrected and "30GB通用" not in corrected:
                print(f"\n[成功] 修正成功！")
            else:
                print(f"\n[失败] 修正未生效")
        else:
            if "10GB通用" in corrected and "30GB定向" in corrected:
                print(f"\n[成功] 保持正确答案！")
            else:
                print(f"\n[警告] 可能有误")

if __name__ == "__main__":
    try:
        test_post_processor()
        print("\n" + "=" * 80)
        print("[完成] 测试完成")
        print("=" * 80)
    except Exception as e:
        print(f"\n[失败] 测试失败：{e}")
        import traceback
        traceback.print_exc()

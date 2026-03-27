"""
完整测试：从表格查询到AI回答
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from agents.enhanced_table_analyzer import ChannelTableAnalyzer
from services.post_processor import AnswerPostProcessor

def test_complete_flow():
    """测试完整的问答流程"""
    print("=" * 80)
    print("完整流程测试")
    print("=" * 80)

    # 1. 初始化
    analyzer = ChannelTableAnalyzer()
    processor = AnswerPostProcessor()

    # 2. 查询表格
    query = "59元潮玩青春卡套餐包含哪些内容？"
    print(f"\n[步骤1] 用户问题：{query}")

    results = analyzer.query(query)
    print(f"[步骤1] 找到 {len(results)} 个相关表格")

    # 3. 提取表格数据
    if results:
        result = results[0]
        table_data = result.answer

        # 去除emoji，避免编码问题
        table_data_clean = table_data.replace('⭐', '').replace('【', '[').replace('】', ']')

        print(f"\n[步骤2] 表格数据（结构化）:")
        print("-" * 80)
        # 只显示前500字符
        print(table_data_clean[:500])
        print("-" * 80)

        # 4. 检查关键字段
        print(f"\n[步骤3] 检查关键字段:")
        if '套内通用流量' in table_data and '10G' in table_data:
            print("  [OK] 正确识别: 套内通用流量 = 10G")
        if '套内定向流量' in table_data and '30G' in table_data:
            print("  [OK] 正确识别: 套内定向流量 = 30G")

        # 检查是否有混淆
        if '30G通用' in table_data:
            print("  [ERROR] 存在混淆: 30G通用流量")
        else:
            print("  [OK] 没有混淆通用流量和定向流量")

    # 5. 模拟AI生成回答（基于表格数据）
    print(f"\n[步骤4] 模拟AI回答生成:")

    # 如果表格数据正确，AI应该生成正确答案
    if results and '套内通用流量' in results[0].answer:
        ai_answer = """【直接回答】
59元潮玩青春卡套餐包含10GB通用流量、30GB定向流量。

【详细说明】
根据表格数据：
- 套内通用流量：10GB
- 套内定向流量：30GB
- 套外语音：0.19元/分钟
- 套外流量：5元/GB
- 全国亲情网：统付版内3个移动号码互打免费

【数据来源】
12月放号独立部分（政策-操作-ID）.docx
"""
    else:
        # 如果表格数据不正确，AI可能生成错误答案
        ai_answer = """【直接回答】
59元潮玩青春卡套餐包含30GB通用流量。

【详细说明】
根据表格数据，套餐包含30GB通用流量。

【数据来源】
12月放号独立部分（政策-操作-ID）.docx
"""

    print(ai_answer)

    # 6. 后处理修正
    print(f"\n[步骤5] 后处理修正:")
    corrected_answer = processor._correct_flow_info(ai_answer)

    # 检查修正效果
    print(f"\n[步骤6] 最终答案验证:")
    if '10GB通用' in corrected_answer and '30GB定向' in corrected_answer:
        print("  [成功] 答案正确：包含10GB通用流量和30GB定向流量")
    elif '10GB通用' in corrected_answer:
        print("  [部分成功] 包含10GB通用流量")
    elif '30GB通用' in corrected_answer:
        print("  [失败] 仍然错误：包含30GB通用流量")
    else:
        print("  [未知] 无法判断")

    return corrected_answer

if __name__ == "__main__":
    try:
        final_answer = test_complete_flow()
        print("\n" + "=" * 80)
        print("[完成] 测试完成")
        print("=" * 80)
    except Exception as e:
        print(f"\n[错误] 测试失败：{e}")
        import traceback
        traceback.print_exc()

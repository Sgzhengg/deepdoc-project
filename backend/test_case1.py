"""
单独测试测试用例1
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from services.post_processor import AnswerPostProcessor

processor = AnswerPostProcessor()

# 测试用例1：只说30GB通用流量
test_input = """【直接回答】
59元潮玩青春卡套餐包含30GB国内通用流量。

【详细说明】
根据表格数据，59元潮玩青春卡套餐包含30GB通用流量、全国亲情网服务。

【数据来源】
12月放号独立部分（政策-操作-ID）.docx
"""

print("输入：")
print(test_input)
print("\n" + "=" * 80 + "\n")

corrected = processor._correct_flow_info(test_input)

print("输出：")
print(corrected)
print("\n" + "=" * 80 + "\n")

# 检查结果
if "10GB通用" in corrected and "30GB定向" in corrected:
    print("[成功] 修正成功！包含10GB通用流量和30GB定向流量")
elif "10GB通用" in corrected:
    print("[部分成功] 修正了通用流量为10GB，但可能缺少定向流量")
else:
    print("[失败] 修正未生效")

"""
概念理解验证器 - 验证业务术语理解是否正确
"""
import re
from typing import List, Dict, Any


class ConceptValidator:
    """概念理解验证器"""

    # 定义关键概念及其验证规则
    CONCEPT_PATTERNS = {
        '倍数': {
            'patterns': [r'(\d+(?:\.\d+)?)倍'],
            'meaning': '比例，需要乘以套餐实收',
            'validation': lambda x: x >= 1.0,
            'example': '1.3倍 = 套餐实收 × 1.3',
            'hint': '倍数是比例，不是固定金额'
        },
        '百分比': {
            'patterns': [r'(\d+)%'],
            'meaning': '比例',
            'validation': lambda x: 0 <= x <= 100,
            'example': '15% = 套餐实收 × 0.15'
        },
        '首充': {
            'patterns': [r'首充(\d+)元'],
            'meaning': '首次充值金额',
            'validation': lambda x: x > 0,
            'example': '首充75元'
        },
        '分成': {
            'patterns': [r'分成(\d+(?:\.\d+)?)元'],
            'meaning': '每月固定分成金额',
            'validation': lambda x: x > 0,
            'example': '分成19.5元/月'
        }
    }

    def validate(self, answer: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """验证概念理解是否正确"""
        issues = []
        warnings = []

        for concept, info in self.CONCEPT_PATTERNS.items():
            # 查找所有匹配的模式
            for pattern in info['patterns']:
                matches = re.findall(pattern, answer)
                for match_str in matches:
                    try:
                        value = float(match_str)

                        # 验证数值合理性
                        if not info['validation'](value):
                            issues.append(f"{concept} '{value}' 数值不合理")

                        # 特殊检查：倍数概念
                        if concept == '倍数':
                            # 检查是否说明了计算方式
                            has_calculation = '×' in answer or '乘以' in answer
                            has_yuan = '元' in answer

                            if has_yuan and not has_calculation:
                                # 如果有"元"但没有说明计算方式，可能是混淆了
                                issues.append(
                                    f"发现倍数概念{value}倍，但可能混淆了概念。"
                                    f"参考示例：套餐实收19.5元 × {value} = {19.5 * value:.2f}元"
                                )
                            elif not has_calculation:
                                warnings.append(
                                    f"发现倍数概念{value}倍，建议说明计算方式（例如：套餐实收 × {value}）"
                                )

                    except ValueError:
                        continue

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }

    def fix_concept_misunderstanding(self, answer: str, context: Dict[str, Any] = None) -> str:
        """尝试修复概念理解错误"""
        # 这里可以实现自动修复逻辑
        # 目前先返回原答案，由人工审核
        return answer

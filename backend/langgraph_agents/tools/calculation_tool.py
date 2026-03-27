"""
CalculationTool - 精确计算工具

修复问题2：LLM不擅长精确计算，使用专门的计算工具确保准确性
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal, getcontext

# 设置Decimal精度
getcontext().prec = 10

logger = logging.getLogger(__name__)


class CalculationTool:
    """
    精确计算工具

    用于处理酬金、费用等需要精确计算的场景
    """

    # 通用计算关键词（不硬编码具体业务术语）
    CALCULATION_KEYWORDS = [
        # 通用计算词汇
        "计算", "总额", "合计", "总和", "总共", "累计",
        # 金额相关（通用）
        "多少元", "多少钱", "费用", "金额", "价格",
        # 运算相关（通用）
        "乘以", "乘", "除以", "除", "加", "减",
        # 比例相关（通用）
        "比例", "百分比", "%",
        # 问题模式（通用）
        "是多少", "如何计算", "怎么算"
    ]

    def __init__(self):
        """初始化计算工具"""
        self.calculation_cache = {}

    def detect_calculation(self, text: str) -> bool:
        """
        检测文本是否包含计算需求

        Args:
            text: 待检测文本

        Returns:
            是否需要计算
        """
        return any(keyword in text for keyword in self.CALCULATION_KEYWORDS)

    def extract_calculation_expressions(self, text: str, context: Dict[str, Any] = None) -> List[str]:
        """
        从文本中提取计算表达式

        Args:
            text: 输入文本
            context: 上下文信息（可能包含检索到的数据）

        Returns:
            提取的计算表达式列表
        """
        expressions = []

        # 模式1: "X元 × Y%" 或 "X元 * Y%"
        pattern1 = r'(\d+(?:\.\d+)?)\s*元?\s*[*×]\s*(\d+(?:\.\d+)?)\s*%?'
        matches1 = re.findall(pattern1, text)
        for match in matches1:
            value = Decimal(str(match[0]))
            percent = Decimal(str(match[1])) / Decimal('100')
            expressions.append(f"{value} * {percent}")

        # 模式2: "X元的Y%" 或 "X的Y%"
        pattern2 = r'(\d+(?:\.\d+)?)\s*元?\s*的\s*(\d+(?:\.\d+)?)\s*%'
        matches2 = re.findall(pattern2, text)
        for match in matches2:
            value = Decimal(str(match[0]))
            percent = Decimal(str(match[1])) / Decimal('100')
            expressions.append(f"{value} * {percent}")

        # 模式3: 从检索到的文档中提取数值和计算关系
        if context and "retrieved_docs" in context:
            doc_expressions = self._extract_from_documents(context["retrieved_docs"])
            expressions.extend(doc_expressions)

        return expressions

    def _extract_from_documents(self, docs: List[Dict]) -> List[str]:
        """
        从检索到的文档中提取计算相关的信息（通用化，无硬编码业务术语）

        Args:
            docs: 文档列表

        Returns:
            提取的表达式列表
        """
        expressions = []

        for doc in docs:
            text = doc.get("text", "")
            source = doc.get("source_document", "")

            # 通用化：查找任何包含数值计算模式的文本（不硬编码具体业务词）
            # 提取类似 "89元 × 15%" 的模式
            pattern = r'(\d+(?:\.\d+)?)\s*元?\s*[*×]\s*(\d+(?:\.\d+)?)\s*%'
            matches = re.findall(pattern, text)
            for match in matches:
                expressions.append(f"{match[0]} * {match[1]} / 100")

        return expressions

    def calculate(self, expression: str) -> Tuple[bool, Any, str]:
        """
        安全地计算表达式

        Args:
            expression: 计算表达式

        Returns:
            (是否成功, 结果, 说明)
        """
        try:
            # 使用Decimal进行精确计算
            result = self._safe_eval(expression)

            if result is not None:
                explanation = self._format_calculation_explanation(expression, result)
                return True, result, explanation

        except Exception as e:
            logger.warning(f"计算失败: {expression}, 错误: {e}")
            return False, None, f"计算失败: {str(e)}"

        return False, None, "无法解析计算表达式"

    def _safe_eval(self, expr: str) -> Optional[Decimal]:
        """
        安全地计算表达式

        只允许数字和基本运算符
        """
        # 清理表达式
        expr = expr.strip()
        expr = expr.replace('×', '*').replace('÷', '/')

        # 验证表达式只包含安全字符
        safe_chars = set('0123456789.+-*/() ')
        if not all(c in safe_chars for c in expr):
            logger.warning(f"表达式包含不安全字符: {expr}")
            return None

        try:
            # 使用Decimal进行计算
            result = eval(expr, {"__builtins__": {}}, {
                "Decimal": Decimal
            })

            # 确保返回Decimal类型
            if isinstance(result, (int, float, Decimal)):
                return Decimal(str(result))

            return None

        except Exception as e:
            logger.warning(f"表达式计算失败: {expr}, 错误: {e}")
            return None

    def _format_calculation_explanation(self, expression: str, result: Decimal) -> str:
        """
        格式化计算说明

        Args:
            expression: 原始表达式
            result: 计算结果

        Returns:
            格式化的说明文本
        """
        # 将表达式转换为更易读的格式
        readable_expr = expression
        readable_expr = readable_expr.replace('*', ' × ').replace('/', ' ÷ ')

        # 格式化结果（保留两位小数）
        if isinstance(result, Decimal):
            formatted_result = f"{result:.2f}"
            # 去除不必要的.00
            if formatted_result.endswith('.00'):
                formatted_result = formatted_result[:-3]

            return f"计算：{readable_expr} = {formatted_result}元"

        return f"计算：{readable_expr} = {result}"

    def analyze_and_calculate(
        self,
        query: str,
        retrieved_docs: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        分析查询并执行计算

        Args:
            query: 用户查询
            retrieved_docs: 检索到的文档

        Returns:
            计算结果字典
        """
        result = {
            "has_calculation": False,
            "calculations": [],
            "total": None,
            "explanation": ""
        }

        # 检测是否需要计算
        if not self.detect_calculation(query):
            return result

        result["has_calculation"] = True

        # 构建上下文
        context = {}
        if retrieved_docs:
            context["retrieved_docs"] = retrieved_docs

        # 提取计算表达式
        expressions = self.extract_calculation_expressions(query, context)

        # 执行计算
        calculations = []
        total = Decimal('0')

        for expr in expressions:
            success, value, explanation = self.calculate(expr)
            if success:
                calculations.append({
                    "expression": expr,
                    "result": float(value),
                    "explanation": explanation
                })
                total += value

        result["calculations"] = calculations

        if calculations:
            result["total"] = float(total)
            result["explanation"] = self._generate_calculation_summary(calculations, total)

        return result

    def _generate_calculation_summary(self, calculations: List[Dict], total: Decimal) -> str:
        """
        生成计算总结说明

        Args:
            calculations: 计算列表
            total: 总计

        Returns:
            总结说明
        """
        if not calculations:
            return ""

        parts = []
        for calc in calculations:
            parts.append(calc["explanation"])

        if len(calculations) > 1:
            total_str = f"{total:.2f}".rstrip('0').rstrip('.')
            parts.append(f"总计：{total_str}元")

        return "\n".join(parts)


# 全局单例
_calculation_tool: Optional[CalculationTool] = None


def get_calculation_tool() -> CalculationTool:
    """获取计算工具实例（单例模式）"""
    global _calculation_tool
    if _calculation_tool is None:
        _calculation_tool = CalculationTool()
    return _calculation_tool

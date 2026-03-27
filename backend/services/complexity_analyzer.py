"""
QueryComplexityAnalyzer - 查询复杂度评估器

根据用户查询的特征评估其复杂度，决定使用哪个模型：
- 简单查询 → 7B 模型（快速响应）
- 复杂查询 → 14B 模型（更准确）
"""

import logging
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """查询意图类型"""
    # 简单查询
    SIMPLE_SEARCH = "simple_search"          # 简单搜索
    DEFINITION = "definition"                # 概念定义
    BASIC_INFO = "basic_info"                # 基础信息查询

    # 中等查询
    TABLE_QUERY = "table_query"              # 表格查询
    COMPARISON = "comparison"                # 对比分析
    STATUS_CHECK = "status_check"            # 状态查询

    # 复杂查询
    CALCULATION = "calculation"              # 计算类
    COMPLEX_ANALYSIS = "complex_analysis"     # 复杂分析
    MULTI_STEP = "multi_step"                # 多步推理
    AMBIGUOUS = "ambiguous"                  # 模糊查询


@dataclass
class ComplexityResult:
    """复杂度评估结果"""
    score: float              # 复杂度分数 (0.0 - 1.0)
    intent: QueryIntent       # 查询意图
    use_large_model: bool     # 是否使用大模型
    confidence: float         # 评估置信度
    reasons: list[str]        # 评分原因


class QueryComplexityAnalyzer:
    """
    查询复杂度评估器

    基于多个维度评估查询复杂度：
    1. 查询长度
    2. 关键词复杂度
    3. 意图类型
    4. 数值/计算相关
    5. 多条件/多步推理
    """

    # 复杂查询关键词
    COMPLEX_KEYWORDS = {
        'calculation': [
            '计算', '算', '多少钱', '费用', '酬金', '分成', '补贴',
            '总计', '合计', '乘', '除', '百分比', '%', '利率',
            '折后价', '公式', '折算', '结算', '实收', '原价', '折扣价',
            '多少元', '如何计算', '怎么算', '求', '等于', '相差'
        ],
        'comparison': [
            '对比', '区别', '差异', '比较', '哪个好', '哪个便宜',
            '优缺点', '不同', '相比', '之间', ' versus ', 'vs',
            '分别', '各', '分别是什么', '有什么区别', '相同', '不同之处',
            '区别是什么', '对比一下', '差异在于'
        ],
        'complex_analysis': [
            '分析', '评估', '判断', '为什么', '原因', '如何',
            '怎么样', '是否', '能否', '可以', '建议', '推荐',
            '含义', '解释', '说明', '详细说明', '是什么意思'
        ],
        'multi_step': [
            '然后', '接着', '再', '之后', '同时', '另外', '还有',
            '如果', '那么', '那么就', '在这种情况下', '还有哪些',
            '还有吗', '其他的', '分别', '分别是什么'
        ]
    }

    # 简单查询关键词
    SIMPLE_KEYWORDS = [
        '是什么', '什么是', '怎么联系', '电话', '地址', '在哪里',
        '多少', '几个', '有没有', '是否', '时间', '什么时候',
        '谁', '哪个部门', '如何办理', '流程'
    ]

    # 数值模式
    NUMERIC_PATTERNS = [
        r'\d+元', r'\d+%', r'\d+\.\d+', r'\d+户',
        r'\d+星级', r'\d+星', r'\d+倍'
    ]

    def __init__(self, threshold: float = 0.6):
        """
        初始化复杂度评估器

        Args:
            threshold: 使用大模型的阈值 (0.0-1.0)
        """
        self.threshold = threshold
        self._compile_patterns()

    def _compile_patterns(self):
        """编译正则表达式模式"""
        self.numeric_patterns = [
            re.compile(pattern) for pattern in self.NUMERIC_PATTERNS
        ]

    def analyze(self, query: str, chat_history: list = None) -> ComplexityResult:
        """
        分析查询复杂度

        Args:
            query: 用户查询文本
            chat_history: 对话历史（用于检测追问）

        Returns:
            ComplexityResult: 复杂度评估结果
        """
        reasons = []
        scores = {}

        # 检测是否有对话历史（多轮对话）
        has_history = chat_history and len(chat_history) > 0
        if has_history:
            scores['history'] = 0.2
            reasons.append("多轮对话上下文")

        # 1. 查询长度评分
        length_score, length_reason = self._score_length(query)
        scores['length'] = length_score
        if length_reason:
            reasons.append(length_reason)

        # 2. 关键词复杂度评分
        keyword_score, keyword_reasons = self._score_keywords(query)
        scores['keywords'] = keyword_score
        reasons.extend(keyword_reasons)

        # 3. 数值内容评分
        numeric_score, numeric_reason = self._score_numeric(query)
        scores['numeric'] = numeric_score
        if numeric_reason:
            reasons.append(numeric_reason)

        # 4. 意图识别
        intent = self._classify_intent(query)

        # 5. 特殊模式检测
        pattern_score, pattern_reason = self._score_patterns(query)
        scores['patterns'] = pattern_score
        if pattern_reason:
            reasons.append(pattern_reason)

        # 计算综合复杂度分数
        final_score = self._calculate_final_score(scores, intent)

        # 判断是否使用大模型
        use_large_model = final_score >= self.threshold

        # 计算置信度
        confidence = self._calculate_confidence(scores)

        result = ComplexityResult(
            score=round(final_score, 3),
            intent=intent,
            use_large_model=use_large_model,
            confidence=round(confidence, 3),
            reasons=reasons[:5]  # 只保留前5个原因
        )

        logger.info(
            f"复杂度分析: score={result.score}, "
            f"intent={intent.value}, "
            f"use_large_model={use_large_model}, "
            f"reasons={result.reasons}"
        )

        return result

    def _score_length(self, query: str) -> tuple[float, str]:
        """基于查询长度评分"""
        length = len(query)

        if length < 10:
            return 0.1, ""
        elif length < 30:
            return 0.2, ""
        elif length < 50:
            return 0.3, ""
        elif length < 80:
            return 0.5, "查询长度中等"
        else:
            return 0.7, "查询内容较长，可能包含复杂需求"

    def _score_keywords(self, query: str) -> tuple[float, list[str]]:
        """基于关键词评分"""
        score = 0.0
        reasons = []

        query_lower = query.lower()

        # 检测追问模式（多轮对话）
        followup_patterns = ['还有', '其他', '另外', '那', '那么', '接下来', '分别']
        is_followup = any(pattern in query for pattern in followup_patterns)
        if is_followup:
            score += 0.15
            reasons.append("追问/多轮对话")

        # 检测"分别"类问题（需要分别解释多个概念）
        if '分别' in query or '各' in query:
            score += 0.25
            reasons.append("需要分别分析")

        # 检测简单关键词（降低复杂度）- 但如果是追问则不降低
        simple_count = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in query)
        if simple_count > 0 and simple_count == len(re.findall(
            '|'.join(self.SIMPLE_KEYWORDS), query
        )):
            # 只有简单关键词，且不是追问
            if not is_followup:
                score -= 0.1
                reasons.append("简单信息查询")

        # 检测计算类关键词
        calc_count = sum(1 for kw in self.COMPLEX_KEYWORDS['calculation'] if kw in query)
        if calc_count > 0:
            score += 0.35
            reasons.append(f"包含计算/费用相关查询")

        # 检测对比类关键词 - 提高评分
        comp_count = sum(1 for kw in self.COMPLEX_KEYWORDS['comparison'] if kw in query)
        if comp_count > 0:
            score += 0.45  # 从0.3提高到0.45
            reasons.append("包含对比分析")

        # 检测复杂分析关键词
        analysis_count = sum(1 for kw in self.COMPLEX_KEYWORDS['complex_analysis'] if kw in query)
        if analysis_count > 0:
            score += 0.25
            reasons.append("需要分析推理")

        # 检测多步推理关键词
        multi_count = sum(1 for kw in self.COMPLEX_KEYWORDS['multi_step'] if kw in query)
        if multi_count > 0:
            score += 0.25  # 从0.2提高到0.25
            reasons.append("可能需要多步推理")

        return min(score, 1.0), reasons

    def _score_numeric(self, query: str) -> tuple[float, str]:
        """基于数值内容评分"""
        has_numeric = any(pattern.search(query) for pattern in self.numeric_patterns)

        if has_numeric:
            return 0.2, "包含数值数据"
        return 0.0, ""

    def _score_patterns(self, query: str) -> tuple[float, str]:
        """检测特殊模式"""
        score = 0.0
        reasons = []

        # 检测问号数量（多个问题可能表示复杂查询）
        question_count = query.count('？') + query.count('?')
        if question_count > 1:
            score += 0.15
            reasons.append("包含多个问题")

        # 检测括号内容（补充说明）
        if '(' in query or '（' in query:
            score += 0.1
            reasons.append("包含补充说明")

        # 检测顿号/分号（多条件）
        if '、' in query or ';' in query or '；' in query:
            score += 0.15
            reasons.append("包含多个条件")

        return score, "、".join(reasons)

    def _classify_intent(self, query: str) -> QueryIntent:
        """分类查询意图"""
        # 优先检测计算类
        if any(kw in query for kw in self.COMPLEX_KEYWORDS['calculation']):
            return QueryIntent.CALCULATION

        # 检测对比类
        if any(kw in query for kw in self.COMPLEX_KEYWORDS['comparison']):
            return QueryIntent.COMPARISON

        # 检测表格查询
        if '表格' in query or '表' in query or '清单' in query:
            return QueryIntent.TABLE_QUERY

        # 检测多步推理
        if any(kw in query for kw in self.COMPLEX_KEYWORDS['multi_step']):
            return QueryIntent.MULTI_STEP

        # 检测复杂分析
        if any(kw in query for kw in self.COMPLEX_KEYWORDS['complex_analysis']):
            return QueryIntent.COMPLEX_ANALYSIS

        # 检测状态查询
        if any(kw in query for kw in ['状态', '进度', '是否', '有没有']):
            return QueryIntent.STATUS_CHECK

        # 默认为简单搜索
        return QueryIntent.SIMPLE_SEARCH

    def _calculate_final_score(self, scores: Dict[str, float], intent: QueryIntent) -> float:
        """计算最终复杂度分数"""
        # 基础分数：各维度加权平均
        # 根据是否有history调整权重
        if 'history' in scores:
            weights = {
                'length': 0.12,
                'keywords': 0.40,
                'numeric': 0.12,
                'patterns': 0.21,
                'history': 0.15  # 对话历史权重
            }
        else:
            weights = {
                'length': 0.15,
                'keywords': 0.45,
                'numeric': 0.15,
                'patterns': 0.25
            }

        base_score = sum(scores.get(k, 0) * w for k, w in weights.items())

        # 根据意图调整 - 提高对比类和多步推理类评分
        intent_modifiers = {
            QueryIntent.SIMPLE_SEARCH: -0.1,
            QueryIntent.DEFINITION: -0.05,
            QueryIntent.BASIC_INFO: 0.0,
            QueryIntent.TABLE_QUERY: 0.1,
            QueryIntent.COMPARISON: 0.3,  # 从0.2提高到0.3
            QueryIntent.STATUS_CHECK: 0.0,
            QueryIntent.CALCULATION: 0.35,  # 从0.3提高到0.35
            QueryIntent.COMPLEX_ANALYSIS: 0.25,
            QueryIntent.MULTI_STEP: 0.4,  # 从0.35提高到0.4
            QueryIntent.AMBIGUOUS: 0.2
        }

        final_score = base_score + intent_modifiers.get(intent, 0)

        # 限制范围在 [0, 1]
        return max(0.0, min(1.0, final_score))

    def _calculate_confidence(self, scores: Dict[str, float]) -> float:
        """计算评估置信度"""
        # 如果分数集中在极端值（0或1），置信度更高
        score_values = list(scores.values())

        if not score_values:
            return 0.5

        avg_score = sum(score_values) / len(score_values)

        # 极端值有更高置信度
        if avg_score < 0.2 or avg_score > 0.8:
            return 0.85
        elif avg_score < 0.4 or avg_score > 0.7:
            return 0.7
        else:
            return 0.6


# 全局单例
_analyzer: Optional[QueryComplexityAnalyzer] = None


def get_complexity_analyzer(threshold: float = 0.6) -> QueryComplexityAnalyzer:
    """
    获取复杂度分析器实例（单例模式）

    Args:
        threshold: 使用大模型的阈值

    Returns:
        QueryComplexityAnalyzer 实例
    """
    global _analyzer
    if _analyzer is None or _analyzer.threshold != threshold:
        _analyzer = QueryComplexityAnalyzer(threshold=threshold)
    return _analyzer

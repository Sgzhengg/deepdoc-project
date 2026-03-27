"""
增强的查询路由器

智能判断查询复杂度，动态选择合适的模型和提示词模板
"""

import re
import logging
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """查询类型"""
    SIMPLE = "simple"              # 简单查询
    POLICY = "policy"              # 政策查询
    PRODUCT = "product"            # 产品信息
    COMPLEX = "complex"            # 复杂查询
    COMPARISON = "comparison"      # 对比分析
    CONDITIONAL = "conditional"    # 条件判断
    CALCULATION = "calculation"    # 计算类
    MULTI_STEP = "multi_step"      # 多步骤
    FOLLOW_UP = "follow_up"        # 追问


class ModelSize(Enum):
    """模型大小"""
    SMALL_7B = "7b"
    LARGE_14B = "14b"


@dataclass
class RouteDecision:
    """路由决策结果"""
    model_size: ModelSize
    query_type: QueryType
    prompt_template: str
    complexity_score: float
    reasons: List[str]
    is_follow_up: bool


class EnhancedQueryRouter:
    """
    增强的查询路由器

    根据查询的多个维度判断复杂度，选择合适的模型和提示词模板
    """

    # 计算关键词
    CALCULATION_KEYWORDS = [
        "多少钱", "如何计算", "怎么算", "费用", "金额",
        "提成", "佣金", "分成", "激励", "补贴",
        "合计", "总共", "总计"
    ]

    # 对比关键词
    COMPARISON_KEYWORDS = [
        "对比", "差异", "区别", "比较", "不同",
        "相同", "优势", "劣势"
    ]

    # 条件关键词
    CONDITIONAL_KEYWORDS = [
        "如果", "是否", "能不能", "是否符合",
        "条件", "要求", "前提", "在...情况下"
    ]

    # 追问指示词
    FOLLOW_UP_INDICATORS = [
        "那", "那如果", "那...呢", "这个", "它",
        "刚才", "上述", "同样", "相应的"
    ]

    # 复杂逻辑标记
    COMPLEX_MARKERS = [
        "然后", "接着", "之后", "同时", "另外",
        "不仅", "而且", "但是", "不过",
        "除了", "包括", "以及"
    ]

    def __init__(self, threshold: float = 5.0):
        """
        初始化路由器

        Args:
            threshold: 使用14B模型的复杂度阈值（降低阈值让更多问题用14B）
        """
        self.threshold = threshold
        logger.info(f"EnhancedQueryRouter initialized with threshold={threshold}")

    def route(
        self,
        query: str,
        chat_history: List[Dict[str, str]] = None
    ) -> RouteDecision:
        """
        路由查询到合适的模型和提示词模板

        Args:
            query: 用户查询
            chat_history: 对话历史

        Returns:
            RouteDecision: 路由决策
        """
        logger.info(f"Routing query: {query[:50]}...")

        # 1. 检查是否是追问
        is_follow_up = self._is_follow_up(query, chat_history)

        # 2. 分析查询类型
        query_type = self._classify_query_type(query)

        # 3. 计算复杂度分数
        complexity_score = self._calculate_complexity(query, query_type, chat_history)

        # 4. 选择模型
        model_size = self._select_model(complexity_score, is_follow_up)

        # 5. 选择提示词模板
        prompt_template = self._select_prompt_template(query_type, model_size)

        # 6. 生成原因说明
        reasons = self._explain_decision(
            complexity_score, query_type, is_follow_up, model_size
        )

        decision = RouteDecision(
            model_size=model_size,
            query_type=query_type,
            prompt_template=prompt_template,
            complexity_score=complexity_score,
            reasons=reasons,
            is_follow_up=is_follow_up
        )

        logger.info(
            f"Route decision: {model_size.value} model, "
            f"type={query_type.value}, score={complexity_score:.1f}"
        )

        return decision

    def _is_follow_up(self, query: str, history: List[Dict]) -> bool:
        """检测是否是追问"""
        if not history or len(history) == 0:
            return False

        # 检查指示词
        if any(query.startswith(w) for w in self.FOLLOW_UP_INDICATORS):
            return True

        # 检查指代词
        reference_words = ["它", "这个", "那个", "该"]
        if any(w in query for w in reference_words):
            return True

        # 检查省略主语（短问题）
        if len(query) < 15:
            # 排除直接的完整问题
            if not any(kw in query for kw in ["什么", "如何", "怎么", "哪些"]):
                return True

        return False

    def _classify_query_type(self, query: str) -> QueryType:
        """分类查询类型"""
        # 计算类
        if any(kw in query for kw in self.CALCULATION_KEYWORDS):
            if re.search(r'\d+\.?\d*%|\d+元|\d+期', query):
                return QueryType.CALCULATION

        # 对比类
        if any(kw in query for kw in self.COMPARISON_KEYWORDS):
            return QueryType.COMPARISON

        # 条件类
        if any(kw in query for kw in self.CONDITIONAL_KEYWORDS):
            return QueryType.CONDITIONAL

        # 复杂逻辑
        if any(kw in query for kw in self.COMPLEX_MARKERS):
            return QueryType.MULTI_STEP

        # 政策查询
        if any(kw in query for kw in ["政策", "规定", "办法", "制度"]):
            return QueryType.POLICY

        # 产品信息
        if any(kw in query for kw in ["产品", "套餐", "卡品", "优惠"]):
            return QueryType.PRODUCT

        # 默认为简单查询
        return QueryType.SIMPLE

    def _calculate_complexity(
        self,
        query: str,
        query_type: QueryType,
        history: List[Dict]
    ) -> float:
        """计算查询复杂度分数"""
        score = 0.0

        # 1. 基础分数
        base_scores = {
            QueryType.SIMPLE: 1.0,
            QueryType.POLICY: 2.0,
            QueryType.PRODUCT: 2.0,
            QueryType.COMPLEX: 3.0,
            QueryType.COMPARISON: 5.0,
            QueryType.CONDITIONAL: 4.0,
            QueryType.CALCULATION: 5.0,
            QueryType.MULTI_STEP: 6.0,
            QueryType.FOLLOW_UP: 3.0,
        }
        score += base_scores.get(query_type, 2.0)

        # 2. 查询长度（长问题通常更复杂）
        if len(query) > 50:
            score += 1.0
        if len(query) > 100:
            score += 1.0

        # 3. 实体数量
        entities = self._extract_entities(query)
        if len(entities) >= 3:
            score += 1.0
        if len(entities) >= 5:
            score += 1.0

        # 4. 数值精度要求
        if re.search(r'\d+\.?\d*%|\d+元|\d+期|\d+倍', query):
            score += 1.0

        # 5. 追问加分
        if self._is_follow_up(query, history):
            score += 2.0  # 追问需要上下文理解

        # 6. 多条件加分
        condition_count = query.count("和") + query.count("或") + query.count("且")
        if condition_count >= 2:
            score += 1.0

        # 7. 否定词加分（增加理解难度）
        if any(word in query for word in ["不", "非", "除", "未", "没有"]):
            score += 0.5

        return score

    def _extract_entities(self, query: str) -> List[str]:
        """提取查询中的实体"""
        entities = []

        # 提取金额
        amounts = re.findall(r'\d+(?:\.\d+)?(?:元|块)', query)
        entities.extend(amounts)

        # 提取百分比
        percentages = re.findall(r'\d+(?:\.\d+)?%', query)
        entities.extend(percentages)

        # 提取套餐档次
        tiers = re.findall(r'\d+元(?:套餐|档)', query)
        entities.extend(tiers)

        # 提取渠道类型
        channels = ["社会渠道", "自营厅", "校园渠道", "政企渠道"]
        for channel in channels:
            if channel in query:
                entities.append(channel)

        return entities

    def _select_model(self, complexity_score: float, is_follow_up: bool) -> ModelSize:
        """选择模型大小"""
        # 降低阈值，让更多问题使用14B模型
        if is_follow_up:
            # 追问总是使用14B（需要上下文理解）
            return ModelSize.LARGE_14B

        if complexity_score >= self.threshold:
            return ModelSize.LARGE_14B

        # 边界情况：分数接近阈值时，优先使用14B
        if complexity_score >= self.threshold - 1.0:
            return ModelSize.LARGE_14B

        return ModelSize.SMALL_7B

    def _select_prompt_template(self, query_type: QueryType, model_size: ModelSize) -> str:
        """选择提示词模板"""
        # 追问总是使用追问模板
        if query_type == QueryType.FOLLOW_UP:
            return "follow_up"

        # 14B模型使用复杂模板
        if model_size == ModelSize.LARGE_14B:
            template_map = {
                QueryType.CALCULATION: "calculation",
                QueryType.COMPARISON: "comparison",
                QueryType.CONDITIONAL: "conditional",
                QueryType.MULTI_STEP: "complex",
            }
            return template_map.get(query_type, "complex")

        # 7B模型使用简单模板
        return "simple"

    def _explain_decision(
        self,
        score: float,
        query_type: QueryType,
        is_follow_up: bool,
        model_size: ModelSize
    ) -> List[str]:
        """生成决策原因说明"""
        reasons = []

        reasons.append(f"查询类型: {query_type.value}")
        reasons.append(f"复杂度分数: {score:.1f}")

        if is_follow_up:
            reasons.append("检测到追问，需要上下文理解")

        if model_size == ModelSize.LARGE_14B:
            reasons.append(f"分数 >= {self.threshold:.1f} 或为追问，使用14B模型")
        else:
            reasons.append(f"分数 < {self.threshold:.1f}，使用7B模型")

        return reasons


# 全局单例
_router_instance: Optional[EnhancedQueryRouter] = None


def get_query_router(threshold: float = 5.0) -> EnhancedQueryRouter:
    """获取查询路由器实例（单例模式）"""
    global _router_instance
    if _router_instance is None:
        _router_instance = EnhancedQueryRouter(threshold=threshold)
    return _router_instance


def set_query_router(router: EnhancedQueryRouter):
    """设置查询路由器实例"""
    global _router_instance
    _router_instance = router

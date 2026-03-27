# query_understanding.py
"""
查询理解模块 - 理解用户查询意图，提取实体，生成查询重写
专门针对运营商渠道业务优化
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """查询意图类型"""
    POLICY_QUERY = "policy_query"  # 政策查询
    FEE_CALCULATION = "fee_calculation"  # 费用计算
    COMMISSION_QUERY = "commission_query"  # 佣金查询
    PRODUCT_INFO = "product_info"  # 产品信息
    RULE_EXPLANATION = "rule_explanation"  # 规则说明
    COMPARISON = "comparison"  # 对比分析
    ELIGIBILITY_CHECK = "eligibility_check"  # 资格检查
    GENERAL_SEARCH = "general_search"  # 通用搜索


@dataclass
class QueryEntity:
    """查询实体"""
    entity_type: str  # 实体类型：amount, product, channel, etc.
    value: str  # 实体值
    confidence: float  # 置信度
    position: tuple  # 在查询中的位置


@dataclass
class QueryAnalysis:
    """查询分析结果"""
    original_query: str
    intent: QueryIntent
    entities: List[QueryEntity]
    rewritten_queries: List[str]
    filters: Dict[str, Any]
    query_type: str  # simple, complex, multi_step


class ChannelQueryUnderstander:
    """渠道业务查询理解器"""

    # 套餐档次关键词
    TIER_KEYWORDS = {
        "低档": ["59元以下", "59以下", "低端", "基础"],
        "中低档": ["59-98", "59到98", "59至98", "中低"],
        "中高档": ["99-128", "99到128", "99至128", "中高"],
        "高档": ["129元以上", "129以上", "高端", "129+"]
    }

    # 费用类型关键词
    FEE_TYPE_KEYWORDS = {
        "实名手续费": ["实名", "实名手续费", "开户费"],
        "充值手续费": ["充值", "首充", "充值手续费", "充话费"],
        "套餐分成": ["分成", "分成激励", "套餐分成", "递延分成"],
        "阶段激励": ["阶段激励", "达量激励", "奖励"],
        "充值激励": ["充值激励", "充值奖励"]
    }

    # 业务场景关键词
    SCENARIO_KEYWORDS = {
        "新增": ["新增", "新开", "新入网", "放号"],
        "存量": ["存量", "在网", "老用户"],
        "校园": ["校园", "高校", "大学"],
        "政企": ["政企", "集团", "企业"]
    }

    # 渠道类型关键词
    CHANNEL_KEYWORDS = {
        "社会渠道": ["社会渠道", "代理商", "合作厅"],
        "自营厅": ["自营厅", "自营", "自营渠道"],
        "校园渠道": ["校园渠道", "高校渠道"],
        "线上渠道": ["线上", "互联网", "APP"],
        "带店加盟": ["带店加盟"],
        "委托加盟": ["委托加盟"],
        "终端渠道": ["终端渠道"]
    }

    def __init__(self):
        """初始化查询理解器"""
        logger.info("渠道业务查询理解器初始化完成")

    def understand(self, query: str) -> QueryAnalysis:
        """
        理解查询

        Args:
            query: 用户查询

        Returns:
            QueryAnalysis: 查询分析结果
        """
        logger.info(f"开始分析查询: {query}")

        # 1. 识别意图
        intent = self._classify_intent(query)

        # 2. 提取实体
        entities = self._extract_entities(query)

        # 3. 查询重写
        rewritten_queries = self._rewrite_query(query, intent, entities)

        # 4. 生成过滤条件
        filters = self._generate_filters(intent, entities)

        # 5. 判断查询类型
        query_type = self._determine_query_type(query, intent, entities)

        analysis = QueryAnalysis(
            original_query=query,
            intent=intent,
            entities=entities,
            rewritten_queries=rewritten_queries,
            filters=filters,
            query_type=query_type
        )

        logger.info(f"查询分析完成: intent={intent.value}, entities={len(entities)}")
        return analysis

    def _classify_intent(self, query: str) -> QueryIntent:
        """分类查询意图"""

        # 费用计算类查询
        if any(kw in query for kw in ["多少钱", "如何计算", "怎么算", "费用", "金额", "提成", "佣金"]):
            if "套餐" in query or "分成" in query:
                return QueryIntent.COMMISSION_QUERY
            return QueryIntent.FEE_CALCULATION

        # 对比类查询
        if any(kw in query for kw in ["对比", "差异", "区别", "比较", "不同"]):
            return QueryIntent.COMPARISON

        # 资格检查类查询
        if any(kw in query for kw in ["是否可以", "能不能", "是否符合", "资格", "条件", "要求"]):
            return QueryIntent.ELIGIBILITY_CHECK

        # 规则说明类查询
        if any(kw in query for kw in ["规则", "怎么", "如何", "流程", "说明", "解释"]):
            return QueryIntent.RULE_EXPLANATION

        # 政策查询
        if any(kw in query for kw in ["政策", "规定", "制度", "办法", "通知"]):
            return QueryIntent.POLICY_QUERY

        # 产品信息查询
        if any(kw in query for kw in ["产品", "套餐", "卡品", "优惠", "活动"]):
            return QueryIntent.PRODUCT_INFO

        return QueryIntent.GENERAL_SEARCH

    def _extract_entities(self, query: str) -> List[QueryEntity]:
        """提取查询实体"""
        entities = []

        # 1. 提取金额实体
        amounts = re.findall(r'(\d+(?:\.\d+)?)\s*(?:元|块)', query)
        for amount in amounts:
            entities.append(QueryEntity(
                entity_type="amount",
                value=amount,
                confidence=0.9,
                position=(0, 0)
            ))

        # 2. 提取套餐档次实体
        for tier_name, keywords in self.TIER_KEYWORDS.items():
            for kw in keywords:
                if kw in query:
                    entities.append(QueryEntity(
                        entity_type="tier",
                        value=tier_name,
                        confidence=0.85,
                        position=(0, 0)
                    ))
                    break

        # 3. 提取费用类型实体
        for fee_type, keywords in self.FEE_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in query:
                    entities.append(QueryEntity(
                        entity_type="fee_type",
                        value=fee_type,
                        confidence=0.9,
                        position=(0, 0)
                    ))
                    break

        # 4. 提取业务场景实体
        for scenario, keywords in self.SCENARIO_KEYWORDS.items():
            for kw in keywords:
                if kw in query:
                    entities.append(QueryEntity(
                        entity_type="scenario",
                        value=scenario,
                        confidence=0.85,
                        position=(0, 0)
                    ))
                    break

        # 5. 提取渠道类型实体
        for channel, keywords in self.CHANNEL_KEYWORDS.items():
            for kw in keywords:
                if kw in query:
                    entities.append(QueryEntity(
                        entity_type="channel",
                        value=channel,
                        confidence=0.85,
                        position=(0, 0)
                    ))
                    break

        return entities

    def _rewrite_query(self, original_query: str, intent: QueryIntent,
                      entities: List[QueryEntity]) -> List[str]:
        """查询重写"""
        rewritten = [original_query]

        # 基于意图重写
        if intent == QueryIntent.FEE_CALCULATION:
            # 提取费用计算相关的关键词
            for entity in entities:
                if entity.entity_type == "fee_type":
                    rewritten.append(f"{entity.value} 计算方法 费用标准")
                elif entity.entity_type == "tier":
                    rewritten.append(f"{entity.value}套餐 费用标准 分成规则")

        elif intent == QueryIntent.COMMISSION_QUERY:
            rewritten.append("套餐分成激励 递延分成 分成比例 分成期数")

        elif intent == QueryIntent.ELIGIBILITY_CHECK:
            rewritten.append("考核条件 资格要求 适用范围")

        # 去重
        seen = set()
        unique_rewritten = []
        for q in rewritten:
            if q not in seen:
                seen.add(q)
                unique_rewritten.append(q)

        return unique_rewritten

    def _generate_filters(self, intent: QueryIntent,
                         entities: List[QueryEntity]) -> Dict[str, Any]:
        """生成过滤条件"""
        filters = {}

        for entity in entities:
            if entity.entity_type == "tier":
                filters["tier"] = entity.value
            elif entity.entity_type == "fee_type":
                filters["fee_type"] = entity.value
            elif entity.entity_type == "scenario":
                filters["scenario"] = entity.value
            elif entity.entity_type == "channel":
                filters["channel"] = entity.value

        return filters

    def _determine_query_type(self, query: str, intent: QueryIntent,
                             entities: List[QueryEntity]) -> str:
        """判断查询类型"""
        # 多步骤查询
        if any(kw in query for kw in ["然后", "接着", "之后", "之后", "同时"]):
            return "multi_step"

        # 复杂查询
        if len(entities) >= 3 or intent in [QueryIntent.COMPARISON, QueryIntent.ELIGIBILITY_CHECK]:
            return "complex"

        return "simple"


# 单例模式
_query_understander = None

def get_query_understander() -> ChannelQueryUnderstander:
    """获取查询理解器实例"""
    global _query_understander
    if _query_understander is None:
        _query_understander = ChannelQueryUnderstander()
    return _query_understander

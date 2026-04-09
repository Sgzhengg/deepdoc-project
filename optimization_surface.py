#!/usr/bin/env python3
"""
DeepDoc 优化表面文件 - Autoresearch 专用
====================================
这是 Karpathy Loop 中唯一允许修改的文件。
所有 LangGraph prompt、Qdrant 配置、查询重写、表格处理逻辑必须集中在这里。
禁止在此文件外修改任何检索/提示相关代码。
"""

from typing import Dict, List, Any, Optional
import json

# ====================== 1. 查询重写 & 同义词扩展（重点优化区） ======================
# 渠道政策标准术语映射表（用于查询归一化）
# 注意：这是从口语/变体到标准术语的映射，用于提高检索召回率
TERM_NORMALIZATION_MAP: Dict[str, str] = {
    # 酬金/激励类（注意：不要全局替换"激励"，因为它会破坏其他标准术语）
    "酬金": "手续费",
    "佣金": "手续费",
    "服补激励": "服务运营激励",
    "服补": "服务运营激励",
    "阶段激励": "服务运营激励",
    "服务补贴": "服务运营激励",
    "套餐分润": "套餐分成",
    "递延分成": "套餐分成",
    "实收套餐分成": "套餐分成",
    "高价值激励积分": "套餐分成",

    # 渠道类型
    "核心店": "核心厅店",
    "自营厅": "核心厅店",
    "核心渠道": "核心厅店",
    "自营厅店": "核心厅店",
    "普通店": "普通渠道",
    "普通代理": "普通渠道",
    "代理商": "普通渠道",
    "社会渠道": "普通渠道",
    "委托店": "委托厅店",
    "委托代理": "委托厅店",
    "加盟店": "委托厅店",

    # 计算相关
    "实际收费": "实收",
    "折后实收": "实收",
    "实际金额": "实收",
    "折扣后": "折后",
    "优惠后": "折后",
    "首次充值": "首充",
    "第一次充值": "首充",
    "首充款": "首充",
    "话费充值": "充值",
    "充值缴费": "充值",
    "缴费": "充值",

    # 考核相关
    "考核标准": "考核规则",
    "考核办法": "考核规则",
    "考核要求": "考核规则",
    "达标规则": "考核规则",
    # 费用和比例相关的映射容易导致误替换，暂时移除
    # "费用标准": "标准",
    # "激励标准": "标准",
    # "酬金标准": "标准",
    # "费率": "比例",
    # "分成比例": "比例",
    # "激励比例": "比例",
    # "系数": "比例",

    # 产品相关
    # "全家享": "全家享套餐",  # 移除，容易导致重复
    "全家享套餐129": "全家享套餐",
    "129全家享": "全家享套餐",
    "129套餐": "129元套餐",
    # "129元": "129元套餐",  # 移除，容易导致重复
    "119套餐": "119元套餐",
    # "119元": "119元套餐",  # 移除，容易导致重复
    "核心产品": "重点产品",
    "主力产品": "重点产品",
    "重点业务": "重点产品",

    # 费用类型
    "首次充值手续费": "首充手续费",
    "首充酬金": "首充手续费",
    "新入网首充": "首充手续费",
    "充值酬金": "充值手续费",
    "充值激励": "充值手续费",

    # 其他常见变体
    "新入网": "放号",
    "开户": "放号",
    "发展新用户": "放号",
    "产能达量": "达量",
    "考核达量": "达量",
    "销售门槛": "达量",
    "属地率": "属地",
    "属地考核": "属地",
    "本地登录": "属地",
    "实名制": "实名",
    "实名手续费": "实名",
    "副卡": "万能副卡",
    "万能副": "万能副卡",
    "七折": "7折",
    "7折优惠": "7折",
    "折扣优惠": "7折",
    "新入网七折优惠": "7折",
    "流量赠送": "流量扩容",
    "扩容优惠": "流量扩容",
}

# 查询扩展关键词集合（用于生成额外的检索查询）
QUERY_EXPANSION_TERMS: Dict[str, List[str]] = {
    "手续费": ["酬金", "激励", "佣金", "费用", "结算"],
    "服务运营激励": ["服补", "阶段激励", "服务补贴"],
    "套餐分成": ["实收套餐分成", "高价值激励积分", "递延分成", "套餐分润"],
    "核心厅店": ["核心店", "自营厅", "核心渠道", "自营厅店"],
    "普通渠道": ["普通店", "普通代理", "代理商", "社会渠道"],
    "委托厅店": ["委托店", "委托代理", "加盟店"],
    "充值": ["话费充值", "充值缴费", "缴费"],
    "首充": ["首次充值", "第一次充值", "首充款"],
}

def rewrite_query(query: str) -> str:
    """
    查询重写（Agent 重点优化方向）

    功能：将用户查询中的各种变体术语归一化为标准术语，提高检索召回率

    策略：单轮替换，按长度从长到短依次替换，避免重复替换

    示例：
    - "核心店的酬金标准" -> "核心厅店的手续费标准"
    - "委托代理的服补激励" -> "委托厅店的服务运营激励"
    """
    rewritten = query

    # 按长度排序，优先处理长词匹配（避免短词误替换）
    # 例如：先匹配"服务运营激励"(7字)，再匹配"服补"(2字)
    sorted_terms = sorted(
        TERM_NORMALIZATION_MAP.items(),
        key=lambda x: len(x[0]),
        reverse=True
    )

    # 标记已被替换的文本位置，避免重叠替换
    replaced_positions = []

    for variant, standard in sorted_terms:
        start = 0
        while True:
            # 查找下一个匹配位置
            pos = rewritten.find(variant, start)
            if pos == -1:
                break

            # 检查这个位置是否已被替换
            is_overlapping = False
            for replaced_start, replaced_end in replaced_positions:
                if not (pos + len(variant) <= replaced_start or pos >= replaced_end):
                    is_overlapping = True
                    break

            if not is_overlapping:
                # 执行替换
                rewritten = rewritten[:pos] + standard + rewritten[pos + len(variant):]
                # 记录替换位置（注意：rewritten 已经改变，需要调整后续位置）
                replaced_positions.append((pos, pos + len(standard)))
                # 调整之前记录的位置（因为文本长度可能变化）
                length_diff = len(standard) - len(variant)
                replaced_positions = [
                    (s + length_diff if s > pos else s,
                     e + length_diff if e > pos else e)
                    for s, e in replaced_positions
                ]
                # 更新搜索起点
                start = pos + len(standard)
            else:
                # 跳过这个重叠的匹配
                start = pos + len(variant)

    return rewritten


# ====================== 2. Qdrant 检索配置（混合检索重点） ======================
QDRANT_CONFIG = {
    "top_k": 30,                    # 当前基线已提升，可继续优化
    "score_threshold": 0.65,
    "vector_weight": 0.7,
    "keyword_weight": 0.3,
    "fusion_method": "rrf",         # RRF / dbsf / weighted_sum
    "use_hybrid": True,             # 是否强制使用 /search/hybrid
    # 表格专用 filter（Agent 可动态调整）
    "table_filters": {
        "must": [{"key": "doc_type", "match": {"value": "table"}}],
        "should": []  # Agent 可在此添加更多 payload 条件
    }
}

def build_qdrant_payload(query: str, is_table_query: bool = False) -> Dict:
    """构建 Qdrant 查询 payload（Agent 重点优化区）"""
    rewritten = rewrite_query(query)
    
    payload = {
        "query": rewritten,
        "top_k": QDRANT_CONFIG["top_k"],
        "score_threshold": QDRANT_CONFIG["score_threshold"],
    }
    
    if QDRANT_CONFIG["use_hybrid"]:
        payload.update({
            "fusion_method": QDRANT_CONFIG["fusion_method"],
            "vector_weight": QDRANT_CONFIG["vector_weight"],
            "keyword_weight": QDRANT_CONFIG["keyword_weight"],
        })
    
    # 表格查询特殊处理
    if is_table_query or any(kw in query for kw in ["费用", "激励", "门槛", "ID", "prod.", "JYPT", "SH", "FWYY"]):
        payload["filter"] = QDRANT_CONFIG["table_filters"]
    
    return payload


# ====================== 3. LangGraph 多 Agent Prompt（核心提示工程区） ======================
LANGGRAPH_PROMPTS: Dict[str, str] = {
    "intent_recognizer": """你是一个中国移动渠道政策专家。
用户查询: {query}
请判断查询意图（单选）：
A. 套餐内容/资费查询
B. 手续费/酬金/激励查询
C. 办理路径/操作指引
D. 考核规则/扣罚规则
E. 表格/费用结构计算
F. 其他
直接返回字母 + 简短理由。""",

    "retrieval_strategist": """根据意图选择最佳检索策略。
意图: {intent}
查询: {query}
可用策略：vector_only / hybrid / table_priority / keyword_first
返回策略名称 + 理由。""",

    "self_rag_evaluator": """评估检索结果质量。
查询: {query}
检索到的上下文: {contexts}
如果质量不足（缺少关键数字/ID/条件），输出 "NEED_MORE_CONTEXT" 并说明缺失内容。
否则输出 "GOOD"。""",

    "reflector": """反思本次回答。
问题: {query}
答案: {answer}
反思：是否存在 hallucination？是否覆盖所有关键点？是否正确处理表格？
输出改进建议（最多3条）。""",

    "answer_generator": """你是中国移动渠道政策智能助手。
严格基于以下上下文回答问题，不要 hallucination。
上下文: {contexts}
用户问题: {query}
要求：
- 数字、ID、条件必须 100% 准确
- 表格数据请用清晰格式呈现
- 必要时说明来源
- 回答要专业、友好、结构化
""",
}

# ====================== 4. 表格专用处理函数（表格匹配痛点优化区） ======================
def enhance_table_payload(doc: Dict) -> Dict:
    """为表格文档增强 payload（Agent 可在此增加更多结构化字段）"""
    # 当前基线
    if doc.get("doc_type") == "table":
        doc["payload"] = {
            **doc.get("payload", {}),
            "table_type": "fee_structure",   # 可扩展：fee / id_list / threshold 等
            "contains_money": True,
            "contains_id": "prod." in str(doc.get("content", "")) or "JYPT" in str(doc.get("content", "")),
        }
    return doc


# ====================== 5. 统一配置导出（供其他模块调用） ======================
def get_optimization_config() -> Dict[str, Any]:
    """返回当前所有优化参数（其他模块通过此函数读取配置）"""
    return {
        "term_normalization_map": TERM_NORMALIZATION_MAP,
        "query_expansion_terms": QUERY_EXPANSION_TERMS,
        "synonym_dict": QUERY_EXPANSION_TERMS,  # 保持向后兼容
        "qdrant_config": QDRANT_CONFIG,
        "langgraph_prompts": LANGGRAPH_PROMPTS,
        "rewrite_query": rewrite_query,
        "build_qdrant_payload": build_qdrant_payload,
        "enhance_table_payload": enhance_table_payload,
    }


# ====================== 6. 调试/日志函数 ======================
def debug_surface(query: str):
    """调试用：打印当前表面配置对某查询的处理结果"""
    print("=== Optimization Surface Debug ===")
    print(f"原始查询: {query}")
    print(f"重写后: {rewrite_query(query)}")
    print(f"Qdrant Payload: {json.dumps(build_qdrant_payload(query), ensure_ascii=False, indent=2)}")
    print("=================================")


# ====================== 初始化提示 ======================
print("✅ optimization_surface.py 已加载 - 当前为 Autoresearch 优化表面")
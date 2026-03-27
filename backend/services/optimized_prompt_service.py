"""
优化的提示词服务 - 解决速度和泛化性问题
核心策略：
1. 压缩提示词长度（减少50% tokens）
2. 分层模块设计（按需加载）
3. 领域自适应（保持泛化性）
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """查询类型"""
    SIMPLE = "simple"           # 简单事实查询
    COMPARISON = "comparison"   # 对比查询
    CALCULATION = "calculation" # 计算查询
    TABLE = "table"            # 表格查询
    POLICY = "policy"          # 政策查询
    NUMERIC = "numeric"        # 数值提取查询（新增）


class OptimizedPromptService:
    """
    优化的提示词服务

    特点：
    - 核心提示词仅80字（比原版减少50%）
    - 扩展模块按需加载
    - 支持领域自适应
    - 内置缓存机制
    """

    # ========== 核心提示词（压缩版，80字） ==========
    CORE_PROMPT = """你是电信政策助手。
【核心原则】
1. 仅基于文档回答，不编造
2. 文档无答案时直接说明
3. 保持简洁准确

【回答格式】
直接回答 + 数据来源"""

    # ========== 扩展模块（按需加载） ==========
    EXTENSIONS = {
        "table": """
【表格数据】
- 仔细阅读列名含义
- 区分不同类别/条件的数值
- 对比类问题分项列出""",

        "calculation": """
【计算类问题】
- 列出计算公式
- 说明数据来源
- 标注计算步骤""",

        "comparison": """
【对比类问题】
- 分项列出差异
- 使用对比格式
- 明确指出相同点和不同点""",

        "policy": """
【政策类问题】
- 注明政策有效期
- 说明适用条件
- 提及限制条件""",

        "numeric": """
【数值精确提取】⚠️重要
- 必须提取完整的数值+单位（如：75元、50元、11.7元、19.5元）
- 对比类问题必须列出每个类别的具体数值
- 格式：类别A = XX元，类别B = XX元
- 禁止使用"包含费用"等模糊表述，必须给出具体数字"""
    }

    # 数值查询关键词（用于自动检测）
    NUMERIC_KEYWORDS = [
        "费用", "手续费", "分成", "激励", "补贴", "元", "多少",
        "T1", "T2", "T3", "属地", "考核", "档位"
    ]

    # ========== 领域适配层（保持泛化性） ==========
    DOMAIN_KEYWORDS = {
        "telecom": ["套餐", "资费", "渠道", "流量", "通话"],
        "policy": ["政策", "规则", "办法", "规定"],
        "product": ["产品", "服务", "功能", "权益"]
    }

    # ========== 缓存 ==========
    _prompt_cache: Dict[str, str] = {}

    @classmethod
    def detect_query_type(cls, query: str, context: Any = None) -> QueryType:
        """
        检测查询类型

        Args:
            query: 用户查询
            context: 额外上下文（如是否有表格数据）

        Returns:
            查询类型
        """
        query_lower = query.lower()

        # 优先检测数值查询（费用、手续费相关）
        if any(kw in query for kw in cls.NUMERIC_KEYWORDS):
            # 检查是否包含"结构"、"对比"、"不同"等对比词汇
            if any(kw in query for kw in ["结构", "对比", "不同", "差异", "区别"]):
                return QueryType.NUMERIC  # 数值对比查询
            # 检查是否询问具体数值
            if any(kw in query for kw in ["多少", "是", "如何"]):
                return QueryType.NUMERIC

        # 检测表格相关
        if context and hasattr(context, 'has_table') and context.has_table:
            return QueryType.TABLE
        if any(kw in query for kw in ["表格", "列", "行"]):
            return QueryType.TABLE

        # 检测计算相关
        if any(kw in query for kw in ["计算", "合计", "总计", "乘以", "加上"]):
            return QueryType.CALCULATION

        # 检测对比相关
        if any(kw in query for kw in ["差异", "不同", "对比", "区别", "相比"]):
            return QueryType.COMPARISON

        # 检测政策相关
        if any(kw in query for kw in ["政策", "规定", "办法", "是否可以"]):
            return QueryType.POLICY

        return QueryType.SIMPLE

    @classmethod
    def build_prompt(
        cls,
        query: str,
        context: Optional[List[str]] = None,
        query_type: Optional[QueryType] = None,
        enable_extensions: bool = True
    ) -> str:
        """
        构建优化的提示词

        Args:
            query: 用户查询
            context: 检索到的文档上下文
            query_type: 查询类型（自动检测如果为None）
            enable_extensions: 是否启用扩展模块

        Returns:
            完整提示词
        """
        # 检测缓存
        cache_key = cls._get_cache_key(query, query_type, enable_extensions)
        if cache_key in cls._prompt_cache:
            logger.debug(f"使用缓存的提示词: {cache_key}")
            return cls._prompt_cache[cache_key]

        # 自动检测查询类型
        if query_type is None:
            query_type = cls.detect_query_type(query, context)

        # 构建提示词
        parts = [cls.CORE_PROMPT]

        # 按需添加扩展模块
        if enable_extensions:
            extension = cls.EXTENSIONS.get(query_type.value)
            if extension:
                parts.append(extension)

        # 添加上下文
        if context:
            context_str = cls._format_context(context, query_type)
            parts.append(context_str)

        # 添加问题
        parts.append(f"\n【问题】\n{query}")

        # 组装
        prompt = "\n".join(parts)

        # 缓存
        cls._prompt_cache[cache_key] = prompt

        return prompt

    @classmethod
    def _format_context(cls, context: List[str], query_type: QueryType) -> str:
        """格式化上下文（根据查询类型优化）"""
        if not context:
            return "【文档】\n未找到相关文档"

        lines = ["【文档】"]

        # 根据查询类型调整上下文长度
        max_docs = 5 if query_type == QueryType.TABLE else 3
        max_length = 1200 if query_type == QueryType.TABLE else 800

        for i, doc in enumerate(context[:max_docs], 1):
            doc_text = doc[:max_length] if len(doc) > max_length else doc
            lines.append(f"\n文档{i}:\n{doc_text}")

        return "\n".join(lines)

    @classmethod
    def _get_cache_key(cls, query: str, query_type: Optional[QueryType],
                       enable_extensions: bool) -> str:
        """生成缓存键"""
        type_str = query_type.value if query_type else "auto"
        ext_str = "1" if enable_extensions else "0"
        # 使用查询的前20个字符作为键的一部分
        query_key = query[:20].replace("\n", " ")
        return f"{type_str}_{ext_str}_{query_key}"

    @classmethod
    def clear_cache(cls):
        """清空缓存"""
        cls._prompt_cache.clear()
        logger.info("提示词缓存已清空")

    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "cached_prompts": len(cls._prompt_cache),
            "cache_keys": list(cls._prompt_cache.keys())
        }


class TablePromptService:
    """表格专用提示词服务"""

    # 表格理解提示词
    TABLE_UNDERSTANDING = """你是一个表格数据解析专家。

【表格结构】
这是一个{table_type}类型的表格。
- 列名：{headers}
- 行数：{rows}行

【解析要点】
1. 仔细阅读每一列的含义，不要混淆列名和数据值
2. 对于对比类表格，明确指出"哪个类别"对应"哪个数值"
3. 注意数值的单位（元、%、月等）

【回答格式】
直接回答问题，必要时用结构化格式（如：类别A = 数值1，类别B = 数值2）

【问题】
{query}

【表格数据】
{table_data}"""

    @classmethod
    def build_table_prompt(
        cls,
        query: str,
        table_data: str,
        table_type: str,
        headers: List[str],
        rows: int
    ) -> str:
        """构建表格专用提示词"""
        return cls.TABLE_UNDERSTANDING.format(
            table_type=table_type,
            headers=", ".join(headers),
            rows=rows,
            query=query,
            table_data=table_data
        )


class CompactPromptService:
    """
    超紧凑提示词服务（用于简单查询）

    适用于：
    - 事实性查询
    - 单文档检索
    - 快速响应场景
    """

    ULTRA_COMPACT = """电信政策助手。
规则：1.仅基于文档 2.无答案直说 3.简洁
{context}

问题：{query}"""

    @classmethod
    def build(cls, query: str, context: str = "") -> str:
        """构建超紧凑提示词（40字核心）"""
        return cls.ULTRA_COMPACT.format(
            context=f"文档：{context[:500]}" if context else "",
            query=query
        )


# 便捷函数
def build_optimized_prompt(
    query: str,
    context: Optional[List[str]] = None,
    use_compact: bool = False
) -> str:
    """
    构建优化提示词的便捷函数

    Args:
        query: 用户查询
        context: 文档上下文
        use_compact: 是否使用超紧凑模式

    Returns:
        优化后的提示词
    """
    if use_compact:
        return CompactPromptService.build(query, context[0] if context else "")
    else:
        return OptimizedPromptService.build_prompt(query, context)


def build_table_prompt(
    query: str,
    table_data: str,
    table_type: str = "general",
    headers: List[str] = None,
    rows: int = 0
) -> str:
    """构建表格专用提示词的便捷函数"""
    return TablePromptService.build_table_prompt(
        query=query,
        table_data=table_data,
        table_type=table_type,
        headers=headers or [],
        rows=rows
)


# 测试代码
if __name__ == "__main__":
    # 测试提示词长度
    simple_prompt = OptimizedPromptService.build_prompt(
        "29元套餐包含什么？",
        ["套餐包含30GB流量..."]
    )
    print(f"简单查询提示词长度: {len(simple_prompt)} 字符")

    table_prompt = OptimizedPromptService.build_prompt(
        "区域服务商和非区域服务商费用有什么不同？",
        ["表格数据..."],
        query_type=QueryType.TABLE
    )
    print(f"表格查询提示词长度: {len(table_prompt)} 字符")

    ultra_compact = CompactPromptService.build(
        "实名手续费是多少？",
        "5元/户..."
    )
    print(f"超紧凑提示词长度: {len(ultra_compact)} 字符")

    # 缓存统计
    stats = OptimizedPromptService.get_cache_stats()
    print(f"缓存统计: {stats}")

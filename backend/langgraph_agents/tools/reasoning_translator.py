"""
ReasoningTranslator - 推理步骤翻译器

将技术化的推理步骤翻译成用户友好的业务语言
"""

import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ReasoningTranslator:
    """
    推理步骤翻译器

    将Agent内部的技术化推理步骤转换为业务用户可理解的友好语言
    """

    # 意图类型翻译映射（业务语言）
    INTENT_TRANSLATIONS = {
        "search": "正在搜索相关政策文档",
        "table_query": "正在查询表格数据",
        "analyze": "正在分析政策内容",
        "compare": "正在对比不同选项",
        "calculate": "正在计算相关费用",
        "status": "正在查询系统状态",
        "general": "正在查询相关信息"
    }

    # 查询类型翻译映射（业务语言）
    QUERY_TYPE_TRANSLATIONS = {
        "simple": "",
        "complex": "",
        "multi_step": ""
    }

    # 检索策略翻译映射（业务语言）
    STRATEGY_TRANSLATIONS = {
        "vector": "使用智能语义搜索",
        "hybrid": "使用综合搜索方式",
        "table": "使用表格数据查询",
        "adaptive": "使用智能自适应搜索",
        "表格+向量": "使用表格和语义双重搜索",
        "表格+hybrid": "使用表格和综合搜索"
    }

    # 推理步骤详细翻译（技术术语 -> 业务语言）
    # 注意：长的特定模式必须在短的通用模式之前
    STEP_PHRASE_TRANSLATIONS = {
        # === 优先级1：完整短语（带emoji） ===
        # ReasoningAgent 计算类步骤
        "📐 识别计算需求": "💰 识别到需要计算费用",
        "🔢 提取数值数据": "📋 正在提取相关数值",
        "➕ 执行精确计算": "🧮 正在进行精确计算",
        "📄 从文档提取相关数值": "📋 正在从文档中查找数据",
        # ReasoningAgent 对比类步骤
        "⚖️ 识别对比对象": "📊 正在识别对比项目",
        "📋 提取对比信息": "📝 正在提取对比信息",
        "🔍 分析差异": "✅ 正在分析差异内容",
        # ReasoningAgent 表格类步骤
        "📊 查询表格数据": "📋 正在查询表格",
        "✅ 找到": "📚 找到了",
        # ReasoningAgent 通用步骤
        "📖 分析相关文档": "📚 正在分析相关文档",
        "📚 基于": "📖 根据共计",
        "个文档进行推理": "份文档进行分析",
        "个相关结果": "条相关结果",
        "个文档": "份相关文件",

        # === 优先级2：不带emoji的特定短语 ===
        "从表格提取:": "表格中找到:",
        "从文档提取:": "文档中提到:",
        "找到差异说明": "发现差异说明",
        "对比项:": "正在对比:",
        "关键信息:": "发现:",

        # === 优先级3：计算相关 ===
        "计算:": "费用计算:",

        # === 优先级4：单字通用术语（放在最后以避免影响特定短语） ===
        "识别": "正在识别",
        "提取": "正在提取",
        "分析": "正在分析",
        "查询": "正在查询",
        "检索": "正在检索",
        "推理": "正在分析",
        "执行": "正在执行",
        "生成": "正在生成",
    }

    # 常见技术术语的正则模式和翻译（使用函数而非lambda以避免self引用问题）
    @staticmethod
    def _translate_match(match, match_type, groups):
        """翻译匹配结果"""
        if match_type == "intent":
            intent = groups[0] if groups else ""
            return f"📋 正在{ReasoningTranslator._translate_intent_static(intent)}..."
        elif match_type == "intent_with_entities":
            intent = groups[0] if groups else ""
            return f"📋 正在{ReasoningTranslator._translate_intent_static(intent)}..."
        elif match_type == "strategy_with_quality":
            doc_count = groups[1] if len(groups) > 1 else "0"
            return f"📚 找到了 {doc_count} 份相关政策文件"
        elif match_type == "strategy":
            doc_count = groups[1] if len(groups) > 1 else "0"
            return f"📚 找到了 {doc_count} 份相关文件"
        elif match_type == "reasoning":
            return "✅ 已从政策文件中提取相关信息"
        return match.group(0)

    @staticmethod
    def _translate_intent_static(intent: str) -> str:
        """静态方法：翻译意图类型"""
        translations = {
            "search": "搜索相关政策文档",
            "table_query": "查询表格数据",
            "analyze": "分析政策内容",
            "compare": "对比不同选项",
            "calculate": "计算相关费用",
            "status": "查询状态信息",
            "general": "查询相关信息"
        }
        return translations.get(intent, "查询相关信息")

    @classmethod
    def _translate_intent(cls, intent: str) -> str:
        """翻译意图类型"""
        return cls.INTENT_TRANSLATIONS.get(intent, "查询相关信息")

    @classmethod
    def _translate_query_type(cls, query_type: str) -> str:
        """翻译查询类型"""
        return cls.QUERY_TYPE_TRANSLATIONS.get(query_type, "查询")

    @classmethod
    def _translate_strategy(cls, strategy: str) -> str:
        """翻译检索策略"""
        return cls.STRATEGY_TRANSLATIONS.get(strategy, "搜索")

    @classmethod
    def translate_step(cls, step: str) -> str:
        """
        翻译单条推理步骤

        Args:
            step: 原始推理步骤

        Returns:
            翻译后的用户友好步骤
        """
        # 模式1: 🔍 意图: search, 类型: simple, 实体: 2个
        match = re.search(r"🔍 意图:\s*(\w+),\s*类型:\s*(\w+),\s*实体:\s*(\d+)个", step)
        if match:
            intent = match.group(1)
            return cls.INTENT_TRANSLATIONS.get(intent, "正在查询信息")

        # 模式2: 🔍 意图: search, 类型: simple
        match = re.search(r"🔍 意图:\s*(\w+),\s*类型:\s*(\w+)", step)
        if match:
            intent = match.group(1)
            return cls.INTENT_TRANSLATIONS.get(intent, "正在查询信息")

        # 模式3: 📊 检索策略=hybrid, 获得10个文档, 质量=0.85
        # 支持复杂策略名如"表格+向量"
        match = re.search(r"📊 检索策略=([^,]+?),\s*获得(\d+)个文档", step)
        if match:
            strategy = match.group(1).strip()
            doc_count = match.group(2)
            strategy_text = cls.STRATEGY_TRANSLATIONS.get(strategy, "使用搜索功能")
            return f"📚 {strategy_text}，找到 {doc_count} 份相关文件"

        # 模式4: 🧠 推理完成: general / calculation / table_query
        match = re.search(r"🧠 推理完成:\s*(\w+)", step)
        if match:
            result_type = match.group(1)
            if result_type == "calculation":
                return "✅ 费用计算完成"
            elif result_type == "table_query":
                return "✅ 表格数据查询完成"
            elif result_type == "comparison":
                return "✅ 对比分析完成"
            else:
                return "✅ 已找到相关信息"

        # 模式5: 翻译详细步骤中的技术短语
        translated = step
        for old_phrase, new_phrase in cls.STEP_PHRASE_TRANSLATIONS.items():
            translated = translated.replace(old_phrase, new_phrase)

        # 额外的通用替换（处理动态内容）
        # 处理 "基于 X 个文档进行推理"
        match = re.search(r"📖 根据共计\s*(\d+)\s*份文档进行分析", translated)
        if match:
            doc_count = match.group(1)
            translated = f"📖 根据共计 {doc_count} 份相关文件进行分析"

        # 处理 "找到 X 个相关结果"
        match = re.search(r"📚 找到了\s*(\d+)\s*条相关结果", translated)
        if match:
            count = match.group(1)
            translated = f"📚 在表格中找到了 {count} 条相关结果"

        # 处理 "找到 X 个文档" 的其他形式
        match = re.search(r"📚 找到了\s*(\d+)\s*个相关结果", translated)
        if match:
            count = match.group(1)
            translated = f"📚 在表格中找到了 {count} 条相关结果"

        return translated

    @classmethod
    def translate_steps(cls, steps: List[str]) -> List[str]:
        """
        翻译所有推理步骤

        Args:
            steps: 原始推理步骤列表

        Returns:
            翻译后的推理步骤列表
        """
        if not steps:
            return []

        translated = []
        for step in steps:
            translated_step = cls.translate_step(step)
            translated.append(translated_step)

        return translated

    @classmethod
    def format_for_display(cls, steps: List[str]) -> str:
        """
        格式化推理步骤用于显示

        Args:
            steps: 推理步骤列表

        Returns:
            格式化后的字符串
        """
        if not steps:
            return "正在分析您的问题..."

        # 只显示关键步骤，合并相似步骤
        key_steps = []
        for step in steps:
            # 跳过一些技术细节
            if any(skip in step for skip in ["实体:", "迭代:", "递归:"]):
                continue
            key_steps.append(step)

        # 限制显示数量
        display_steps = key_steps[:5]

        return "\n".join(display_steps)

    @classmethod
    def simplify_for_user(cls, steps: List[str]) -> List[str]:
        """
        为普通用户简化推理步骤（业务友好语言）

        只保留用户关心的核心步骤，使用业务化表达

        Args:
            steps: 原始推理步骤

        Returns:
            简化后的步骤列表
        """
        if not steps:
            return ["✅ 已从相关文档中找到答案"]

        # 先翻译所有步骤
        translated = cls.translate_steps(steps)

        # 保留翻译后的关键步骤，过滤掉技术细节
        simplified = []

        # 跳过的步骤模式（技术细节）
        skip_patterns = [
            r"^\s+-",  # 以空格和"-"开头的子步骤
            r"关键信息:",  # 包含"关键信息:"的步骤
            r"docs_retrieved",  # 状态类步骤
            r"iteration:",  # 迭代相关
        ]

        for step in translated:
            # 检查是否应该跳过
            should_skip = False
            for pattern in skip_patterns:
                if re.search(pattern, step):
                    should_skip = True
                    break

            if should_skip:
                continue

            # 保留包含友好emoji的步骤
            if any(emoji in step for emoji in ["📋", "📚", "✅", "🧮", "📊", "🔢", "📖", "💰", "📝"]):
                simplified.append(step)
            # 或者包含业务关键词的步骤
            elif any(kw in step for kw in ["正在", "找到了", "份文件", "条结果", "份相关", "费用"]):
                simplified.append(step)

        # 如果没有关键步骤，添加一个通用步骤
        if not simplified:
            simplified = ["✅ 已从相关文档中找到答案"]

        # 限制最多显示4条（避免信息过载）
        result = simplified[:4]

        # 确保最后有完成标记
        if not any("✅" in step for step in result):
            result.append("✅ 已完成分析")

        return result


# 全局单例
_translator: ReasoningTranslator = None


def get_reasoning_translator() -> ReasoningTranslator:
    """获取推理翻译器实例（单例模式）"""
    global _translator
    if _translator is None:
        _translator = ReasoningTranslator()
    return _translator

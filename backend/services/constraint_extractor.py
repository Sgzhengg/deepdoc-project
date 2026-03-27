# -*- coding: utf-8 -*-
"""
通用约束条件提取模块

从文档中动态提取业务约束条件，支持多种约束模式
"""

import re
import logging
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Constraint:
    """约束条件"""
    condition: str  # 触发条件
    requirement: str  # 约束要求
    constraint_type: str  # 约束类型
    source_doc: str = ""  # 来源文档
    confidence: float = 1.0  # 置信度
    items: List[str] = None  # 列表类约束的条目（Phase 2 新增）


class ConstraintExtractor:
    """通用约束条件提取器"""

    # 约束模式库 - 可配置
    CONSTRAINT_PATTERNS = [
        # 模式: 条件-要求对
        (r"([^。\n]+?)仅限([^。\n]+?)(?:办理|使用|享受)", "exclusive"),
        (r"([^。\n]+?)才可([^。\n]+?)(?:办理|使用|享受)", "conditional"),
        (r"需([^。\n]+?)(?:后)?才([^。\n]+?)(?:办理|使用|享受)", "conditional"),
        (r"([^。\n]+?)要求([^。\n]+?)(?:办理|使用|享受)", "conditional"),

        # 模式: 排除/不包含
        (r"([^。\n]+?)(?:不|非)(?:参与|适用|包含)([^。\n]+?)", "exclusion"),

        # 模式: 门槛条件
        (r"([^。\n]+?)(?:及以上|以上|不低于)([^。\n]+?)", "threshold_min"),
        (r"([^。\n]+?)(?:及以下|以下|不高于)([^。\n]+?)", "threshold_max"),

        # 模式: 时间限制
        (r"([^。\n]+?)(?:天内|个月内|[^。]+?内)(?:办理|使用|享受)", "time_limit"),

        # 模式: 数值关系
        (r"([^。\n]+?)为([^。\n]+?)(?:元|个|GB|MB|%)", "numeric_value"),
    ]

    # Phase 2 新增: 列表类约束模式
    LIST_PATTERNS = [
        # "指定XXX包括：A、B、C" 或 "指定XXX如下：A、B、C"
        (r"指定([^。：]+?)[：:]\s*([^。\n]+)", "designated_list"),
        # "XXX包括：A、B、C" 或 "XXX如下：A、B、C"
        (r"([^。：]{2,10}?)[：:]\s*([^\n、。]+?[、,][^\n、。]+(?:[、,][^\n、。]+)*)", "list_items"),
        # "可选择其中一个办理：A、B、C"
        (r"选择(?:其中)?一个办理[：:]\s*([^。\n]+)", "choice_list"),
        # "有A、B、C等"
        (r"有([^。]{2,15}?)[、,]([^。]+?)(?:等|等[者业务产品])", "etc_list"),
    ]

    # Phase 2 新增: 时间周期模式
    TIME_PERIOD_PATTERNS = [
        # T+n 至 T+m 格式
        (r"T\+(\d+)\s*至\s*T\+(\d+)", "t_range"),
        # Tn-Tm 格式（无+号，如 T3-T12）
        (r"T(\d+)\s*(?:至|-|~)\s*T(\d+)", "t_range_no_plus"),
        # 连续N个月
        (r"连续\s*(\d+)\s*个月", "consecutive_months"),
        # 各发放20%
        (r"各\s*发放\s*(\d+)%", "percentage_each"),
        # 第N至第M个月
        (r"第(\d+)\s*(?:至|-|~)\s*第(\d+)\s*个月", "month_range"),
    ]

    # Phase 3 新增: 表格列表提取模式
    TABLE_LIST_PATTERNS = [
        # 表格标记：【产品名称】、【优惠ID】等
        (r"【产品名称】", "table_product_name"),
        (r"产品ID", "table_product_id"),
        # 产品ID格式：prod. 或 JYPT
        (r"prod\.\d+", "table_prod_id"),
        (r"JYPT\d+", "table_jypt_id"),
    ]

    # 实体识别模式
    ENTITY_PATTERNS = {
        'package': r'(?:29|39|49|59|69|79|89|99|129|149)\s*(?:元)?(?:潮玩青春卡|全家享|融合套餐)',
        'product': r'(?:数智生活包|健康(?:黄金|钻石)?会员|全国亲情网|统付版家庭网|综合意外保障)',
        'channel': r'(?:校园渠道|校园微格|区域服务商|全业务渠道|核心厅店|社会渠道)',
        'card_type': r'(?:万能副卡|主卡|副卡|副号)',
        'incentive': r'(?:套餐分成|首充手续费|实名手续费|服务运营激励|阶段达量积分)',
    }

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化约束提取器

        Args:
            config: 配置字典，可自定义模式和实体
        """
        self.config = config or {}
        self.patterns = config.get('constraint_patterns', self.CONSTRAINT_PATTERNS)
        self.entity_patterns = config.get('entity_patterns', self.ENTITY_PATTERNS)
        self.list_patterns = config.get('list_patterns', self.LIST_PATTERNS)  # Phase 2
        self.time_patterns = config.get('time_period_patterns', self.TIME_PERIOD_PATTERNS)  # Phase 2
        self.constraints_cache = {}  # 文档级缓存
        self.list_cache = {}  # Phase 2: 列表缓存
        self.time_period_cache = {}  # Phase 2: 时间周期缓存

    def extract_from_documents(self, documents: List[Dict]) -> List[Constraint]:
        """
        从文档列表中提取所有约束条件

        Args:
            documents: 文档列表，每个文档包含 text 和 filename/source_document

        Returns:
            约束条件列表
        """
        all_constraints = []

        logger.info(f"🔍 [Phase 2] 约束提取器开始处理 {len(documents)} 个文档")

        for doc in documents:
            doc_text = doc.get("text", "")
            source = doc.get("source_document",
                           doc.get("metadata", {}).get("filename",
                           doc.get("filename", "unknown")))

            # 检查缓存
            if source in self.constraints_cache:
                all_constraints.extend(self.constraints_cache[source])
                continue

            doc_constraints = self._extract_from_text(doc_text, source)

            # Phase 2: 提取列表类约束
            list_constraints = self._extract_list_constraints(doc_text, source)
            doc_constraints.extend(list_constraints)

            self.constraints_cache[source] = doc_constraints
            all_constraints.extend(doc_constraints)

        logger.info(f"📊 [Phase 2] 共提取 {len(all_constraints)} 个约束条件")
        return all_constraints

    def _extract_from_text(self, text: str, source: str) -> List[Constraint]:
        """从单个文档文本中提取约束"""
        constraints = []

        for pattern, constraint_type in self.patterns:
            matches = re.findall(pattern, text, re.MULTILINE | re.DOTALL)
            for match in matches:
                if len(match) >= 2:
                    condition = match[0].strip()
                    requirement = match[1].strip()

                    # 验证约束的有效性
                    if self._is_valid_constraint(condition, requirement):
                        constraint = Constraint(
                            condition=condition,
                            requirement=requirement,
                            constraint_type=constraint_type,
                            source_doc=source
                        )
                        constraints.append(constraint)

        return constraints

    # ========== Phase 2 新增方法 ==========

    def _extract_list_constraints(self, text: str, source: str) -> List[Constraint]:
        """
        提取列表类约束条件（Phase 2 新增）

        用于识别如"指定叠加业务包括：A、B、C"这类列表型信息
        确保回答时不会遗漏列表中的项目
        """
        constraints = []

        for pattern, list_type in self.list_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
            for match in matches:
                if len(match.groups()) >= 2:
                    list_title = match.group(1).strip()
                    list_content = match.group(2).strip()

                    # 解析列表项
                    items = self._parse_list_items(list_content)

                    if items and len(items) >= 2:  # 至少2个条目才算有效列表
                        constraint = Constraint(
                            condition=f"{list_title}列表",
                            requirement=f"必须包含所有{len(items)}个条目",
                            constraint_type=f"list_{list_type}",
                            source_doc=source,
                            items=items
                        )
                        constraints.append(constraint)
                        logger.info(f"✅ [Phase 2] 提取到列表约束: {list_title} ({len(items)}项)")

        return constraints

    def _parse_list_items(self, content: str) -> List[str]:
        """
        解析列表内容，提取各个条目

        支持的分隔符：顿号(、)、逗号(,)、分号(;)、以及 A. B. C. 格式
        Phase 3 增强：支持表格格式提取
        """
        items = []

        # Phase 3: 首先尝试表格格式提取
        items = self._extract_items_from_table_format(content)
        if items and len(items) >= 2:
            logger.info(f"📊 [Phase 3] 从表格格式提取到 {len(items)} 个列表项")
            return items

        # 尝试多种分隔符
        separators = ['、', ',', ';', '\\n']

        for sep in separators:
            if sep in content:
                items = [item.strip() for item in content.split(sep)]
                break

        # 如果没有找到分隔符，尝试 A. B. C. 或 1. 2. 3. 格式
        if not items or len(items) == 1:
            number_pattern = r'([A-Za-z]集|[\d]+集|[A-Za-z]\.|[\d]+\.)([^。；；\n]+)'
            matches = re.findall(number_pattern, content)
            if matches:
                items = [match[1].strip() for match in matches]

        # 过滤空项和过短项
        items = [item for item in items if item and len(item) >= 2]

        return items

    def _extract_items_from_table_format(self, text: str) -> List[str]:
        """
        Phase 3 新增：从表格格式中提取列表项

        处理模式：
        - 产品名称列 + 多行数据（用 | 分隔）
        - 产品ID格式（prod. 或 JYPT）
        - 数智生活包、健康会员等特定产品

        Args:
            text: 包含表格格式内容的文本

        Returns:
            提取到的产品名称列表
        """
        items = []

        # 检测是否包含表格标记
        has_table_marker = any(marker in text for marker in ['【产品名称】', '产品ID', 'prod.', 'JYPT'])
        if not has_table_marker:
            return items

        # 按行处理
        lines = text.split('\n')
        in_table_section = False

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测表格开始
            if '【产品名称】' in line or '产品ID' in line:
                in_table_section = True
                continue

            # 检测表格结束（遇到其他标题或空行）
            if in_table_section and line.startswith('【') and '产品' not in line:
                break

            # 解析表格行
            if in_table_section:
                # 尝试管道符分隔的表格
                if '|' in line:
                    parts = line.split('|')
                    for part in parts:
                        part = part.strip()
                        # 提取产品名称（常见的业务产品）
                        if self._is_valid_product_name(part):
                            items.append(part)

                # 尝试直接提取产品名称模式
                # 匹配：2元数智生活包、5元健康黄金会员、全国亲情网等
                product_patterns = [
                    r'\d+元数智生活包',  # 数智生活包
                    r'\d+元健康(?:黄金|钻石)?会员',  # 健康会员
                    r'全国亲情网',  # 亲情网
                    r'统付版家庭网',  # 家庭网
                    r'综合意外保障',  # 意外保障
                    r'中国移动云盘',  # 云盘
                    r'视频彩铃',  # 彩铃
                ]

                for pattern in product_patterns:
                    matches = re.findall(pattern, line)
                    items.extend(matches)

        # 去重并返回
        return list(set(items))

    def _is_valid_product_name(self, text: str) -> bool:
        """
        判断是否为有效的产品名称

        有效特征：
        - 包含"元"（价格）+ 服务名称
        - 包含"网"、"包"、"会员"、"保障"等关键词
        - 长度在3-30字之间
        """
        if not text or len(text) < 3 or len(text) > 30:
            return False

        # 包含关键词
        keywords = ['元', '网', '包', '会员', '保障', '云盘', '彩铃', '生活', '健康']
        if not any(kw in text for kw in keywords):
            return False

        # 排除表头或无效内容
        invalid_patterns = ['产品名称', '产品ID', '优惠ID', '---', '====']
        if any(pattern in text for pattern in invalid_patterns):
            return False

        return True

    def extract_list_items_for_context(self, text: str, question: str) -> List[str]:
        """
        提取问题相关的列表项（用于上下文增强）

        Args:
            text: 文档文本
            question: 用户问题

        Returns:
            相关列表项
        """
        list_constraints = self._extract_list_constraints(text, "")

        relevant_items = []
        question_lower = question.lower()

        for constraint in list_constraints:
            if constraint.items:
                # 检查问题是否与这个列表相关
                if any(keyword in question_lower for keyword in ["哪些", "包括", "有什么", "包含", "有哪些"]):
                    relevant_items.extend(constraint.items)

        return relevant_items

    def validate_list_completeness(
        self,
        answer: str,
        question: str,
        context: str
    ) -> Tuple[bool, List[str]]:
        """
        验证答案是否完整包含列表中的所有条目（Phase 2 新增）

        Args:
            answer: 系统答案
            question: 用户问题
            context: 检索上下文

        Returns:
            (是否完整, 缺失的条目列表)
        """
        # 从上下文中提取列表
        list_constraints = self._extract_list_constraints(context, "")
        missing_items = []

        answer_lower = answer.lower()

        for constraint in list_constraints:
            if constraint.items:
                # 检查每个条目是否在答案中
                for item in constraint.items:
                    if item.lower() not in answer_lower:
                        missing_items.append(item)

        is_complete = len(missing_items) == 0

        if not is_complete:
            logger.warning(f"⚠️ [Phase 2] 答案缺失列表条目: {missing_items}")

        return is_complete, missing_items

    def extract_time_periods(self, text: str, source: str = "") -> List[Dict[str, Any]]:
        """
        提取时间周期信息（Phase 2 新增，Phase 3 增强）

        用于识别如 "T+3至T+12各发放20%" 或 "T3-T12各发放15%" 这类时间周期约束

        Phase 3 修复：正确解析 T3-T12 格式（T+3 至 T+12 的简写）

        Returns:
            时间周期信息列表
        """
        periods = []

        for pattern, period_type in self.time_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                period_info = {
                    'type': period_type,
                    'match': match.group(0),
                    'groups': match.groups(),
                    'source': source
                }

                # Phase 3: 对于 T3-T12 格式，转换为标准的 T+3 至 T+12
                if period_type == 't_range_no_plus':
                    start_month = int(match.group(1))
                    end_month = int(match.group(2))
                    # 添加解析后的标准格式
                    period_info['start_month'] = start_month
                    period_info['end_month'] = end_month
                    period_info['normalized'] = f"T+{start_month}至T+{end_month}"
                    logger.info(f"📅 [Phase 3] 解析时间周期: {match.group(0)} → T+{start_month}至T+{end_month}")

                # 尝试提取关联的百分比
                # 查找同一句或附近的内容中的百分比
                sentence_end = text.find(match.group(0)) + len(match.group(0)) + 50
                context = text[max(0, text.find(match.group(0)) - 20):sentence_end]
                percentage_match = re.search(r'(\d+)%', context)
                if percentage_match:
                    period_info['percentage'] = int(percentage_match.group(1))

                periods.append(period_info)

        return periods

    def validate_time_period_accuracy(
        self,
        answer: str,
        context: str
    ) -> Tuple[bool, str]:
        """
        验证时间周期的准确性（Phase 2 新增，Phase 3 增强）

        检查答案中的时间周期是否与文档一致

        Phase 3 修复：
        - 正确处理 T3-T12 格式
        - 标准化比较格式（都转换为 T+n 格式）

        Returns:
            (是否准确, 错误描述)
        """
        # 从上下文中提取时间周期
        context_periods = self.extract_time_periods(context)
        # 从答案中提取时间周期
        answer_periods = self.extract_time_periods(answer)

        logger.info(f"🔍 [Phase 3] 时间周期验证:")
        logger.info(f"  - 上下文周期数量: {len(context_periods)}")
        for p in context_periods:
            logger.info(f"    {p}")
        logger.info(f"  - 答案周期数量: {len(answer_periods)}")
        for p in answer_periods:
            logger.info(f"    {p}")

        # 如果上下文中有周期信息但答案中没有
        if context_periods and not answer_periods:
            # 检查答案是否提到了任何时间相关的内容
            time_keywords = ['T1', 'T2', 'T3', '月', '期', '发放']
            has_time_mention = any(kw in answer for kw in time_keywords)
            if has_time_mention:
                logger.warning(f"⚠️ [Phase 3] 答案提到时间但未正确解析周期")

        for ctx_period in context_periods:
            for ans_period in answer_periods:
                # 获取标准化的开始和结束月份
                ctx_start, ctx_end = self._get_normalized_period_range(ctx_period)
                ans_start, ans_end = self._get_normalized_period_range(ans_period)

                logger.info(f"🔍 [Phase 3] 比较: 上下文({ctx_start}-{ctx_end}) vs 答案({ans_start}-{ans_end})")

                if ctx_start is not None and ctx_end is not None:
                    if ans_start is not None and ans_end is not None:
                        # 比较
                        if ctx_start != ans_start or ctx_end != ans_end:
                            # 使用标准化的错误消息
                            ctx_str = f"T+{ctx_start}至T+{ctx_end}"
                            ans_str = f"T+{ans_start}至T+{ans_end}"
                            error = f"⚠️ [Phase 3] 时间周期错误: 答案为{ans_str}，应为{ctx_str}"
                            logger.warning(error)
                            return False, error

        return True, ""

    def _get_normalized_period_range(self, period: Dict[str, Any]) -> Tuple[int, int]:
        """
        Phase 3 新增：获取标准化的时间周期范围

        将各种格式统一转换为 T+n 格式的起始月份

        Args:
            period: 时间周期字典

        Returns:
            (start_month, end_month) 或 (None, None)
        """
        if 'start_month' in period and 'end_month' in period:
            # 已经是标准化格式
            return period['start_month'], period['end_month']

        # 从 groups 中提取
        groups = period.get('groups', [])
        if len(groups) >= 2:
            try:
                start = int(groups[0])
                end = int(groups[1])
                return start, end
            except (ValueError, IndexError):
                pass

        return None, None

    # ======================================

    def _is_valid_constraint(self, condition: str, requirement: str) -> bool:
        """验证约束的有效性"""
        # 过滤掉过短或过长的条件
        if len(condition) < 2 or len(condition) > 50:
            return False
        if len(requirement) < 2 or len(requirement) > 50:
            return False

        # 过滤掉无意义的内容
        skip_words = ['的', '是', '为', '有', '和', '与', '或', '等']
        if condition in skip_words or requirement in skip_words:
            return False

        return True

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        从文本中提取业务实体

        Args:
            text: 输入文本

        Returns:
            实体分类字典
        """
        entities = {
            'package': [],
            'product': [],
            'channel': [],
            'card_type': [],
            'incentive': []
        }

        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, text)
            entities[entity_type] = list(set(matches))  # 去重

        return entities

    def get_relevant_constraints(
        self,
        question: str,
        context: str,
        constraints: List[Constraint]
    ) -> List[Constraint]:
        """
        获取与问题相关的约束条件

        Args:
            question: 用户问题
            context: 检索上下文
            constraints: 所有约束条件列表

        Returns:
            相关的约束条件列表
        """
        relevant = []
        question_lower = question.lower()
        context_lower = context.lower()

        # 提取问题中的实体
        question_entities = self.extract_entities(question)
        all_text = question_lower + " " + context_lower

        for constraint in constraints:
            condition_lower = constraint.condition.lower()
            requirement_lower = constraint.requirement.lower()

            # 检查约束是否与问题相关
            is_relevant = False

            # 1. 检查条件是否在问题或上下文中
            if condition_lower in all_text:
                is_relevant = True

            # 2. 检查实体是否匹配
            for entity_type, entities in question_entities.items():
                if entities:  # 问题中包含该类型实体
                    # 检查约束条件或要求中是否包含相关实体
                    for entity in entities:
                        if entity.lower() in condition_lower or entity.lower() in requirement_lower:
                            is_relevant = True
                            break
                if is_relevant:
                    break

            if is_relevant:
                relevant.append(constraint)

        logger.info(f"从 {len(constraints)} 个约束中筛选出 {len(relevant)} 个相关约束")
        return relevant

    def format_constraints_for_prompt(self, constraints: List[Constraint]) -> str:
        """
        将约束条件格式化为提示词文本

        Args:
            constraints: 约束条件列表

        Returns:
            格式化的约束文本
        """
        if not constraints:
            return ""

        lines = ["## ⚠️ 重要业务约束条件："]

        for i, constraint in enumerate(constraints[:10], 1):  # 最多显示10个
            lines.append(f"{i}. **{constraint.condition}** → {constraint.requirement}")

        lines.append("\n**重要提示**: 请严格遵守上述约束条件，不要违反业务规则！")

        return "\n".join(lines)

    def validate_answer_against_constraints(
        self,
        answer: str,
        question: str,
        constraints: List[Constraint]
    ) -> Tuple[bool, List[str]]:
        """
        验证答案是否违反约束条件

        Args:
            answer: 系统生成的答案
            question: 用户问题
            constraints: 相关约束条件列表

        Returns:
            (是否通过, 违反的约束列表)
        """
        violations = []

        for constraint in constraints:
            if self._check_violation(answer, question, constraint):
                violations.append(f"违反约束: {constraint.condition} 需要 {constraint.requirement}")

        is_valid = len(violations) == 0
        return is_valid, violations

    def _check_violation(self, answer: str, question: str, constraint: Constraint) -> bool:
        """检查是否违反特定约束"""
        answer_lower = answer.lower()
        question_lower = question.lower()
        condition_lower = constraint.condition.lower()

        # 检查条件是否在问题中
        condition_in_question = condition_lower in question_lower

        # 根据约束类型进行检查
        if constraint.constraint_type == "exclusive":
            # "仅限"类约束：答案不能说"支持办理"如果条件不满足
            if condition_in_question:
                # 条件在问题中，检查答案是否错误地宣称可以办理
                positive_keywords = ["可以", "支持", "能够", "允许", "办理"]
                negative_answer = any(kw in answer_lower for kw in positive_keywords)
                if negative_answer:
                    # 需要检查条件是否满足 - 这里简化处理，假设未明确满足则违规
                    if not self._check_condition_met(answer, condition_lower):
                        return True

        elif constraint.constraint_type == "exclusion":
            # 排除类约束：检查是否错误地包含了排除项
            excluded_items = constraint.requirement.lower()
            if excluded_items in answer_lower:
                return True

        elif constraint.constraint_type == "threshold_min":
            # 门槛约束：检查是否满足最低要求
            threshold_value = constraint.requirement.lower()
            # 简化处理：如果答案中提到低于门槛的内容，可能违规
            pass

        return False

    def _check_condition_met(self, answer: str, condition: str) -> bool:
        """检查条件是否满足（简化版本）"""
        # 这是一个简化实现，实际需要更复杂的逻辑
        # 例如：检查答案中是否明确提到了满足条件
        condition_met_keywords = ["满足", "符合", "达到", "具备"]
        return any(kw in answer.lower() for kw in condition_met_keywords)


# 全局实例
_constraint_extractor = None


def get_constraint_extractor(config: Dict[str, Any] = None) -> ConstraintExtractor:
    """获取约束提取器实例"""
    global _constraint_extractor
    if _constraint_extractor is None:
        _constraint_extractor = ConstraintExtractor(config or {})
    return _constraint_extractor


# 从YAML配置加载的便捷函数
def load_config_from_yaml(config_path: str = None) -> Dict[str, Any]:
    """从YAML文件加载配置"""
    import os
    default_config = {
        'constraint_patterns': ConstraintExtractor.CONSTRAINT_PATTERNS,
        'entity_patterns': ConstraintExtractor.ENTITY_PATTERNS
    }

    if config_path and os.path.exists(config_path):
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    return default_config


if __name__ == "__main__":
    # 测试代码
    test_doc = {
        "text": """
        29元潮玩青春卡套餐包含30GB定向流量。万能副卡仅限59元及以上套餐办理。
        实名手续费为5元/户，需叠加指定增值业务才可核算。
        校园渠道和校园微格不参与实名手续费核算。
        """,
        "filename": "test.txt"
    }

    extractor = ConstraintExtractor()
    constraints = extractor.extract_from_documents([test_doc])

    print("提取到的约束条件:")
    for constraint in constraints:
        print(f"- {constraint.condition} → {constraint.requirement} ({constraint.constraint_type})")

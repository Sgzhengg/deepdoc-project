# -*- coding: utf-8 -*-
"""
答案验证模块

提供多维度的答案验证机制
"""

import re
import logging
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """验证问题严重程度"""
    CRITICAL = "critical"  # 严重错误，必须修正
    WARNING = "warning"    # 警告，建议修正
    INFO = "info"          # 信息，可忽略


@dataclass
class ValidationIssue:
    """验证问题"""
    issue_type: str  # 问题类型
    severity: ValidationSeverity  # 严重程度
    message: str  # 问题描述
    suggestion: str = ""  # 修改建议
    location: str = ""  # 问题位置


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool  # 是否通过验证
    score: float  # 验证得分 (0-100)
    issues: List[ValidationIssue] = field(default_factory=list)

    def add_issue(self, issue: ValidationIssue):
        """添加问题"""
        self.issues.append(issue)
        # 根据严重程度调整得分
        if issue.severity == ValidationSeverity.CRITICAL:
            self.score = max(0, self.score - 20)
        elif issue.severity == ValidationSeverity.WARNING:
            self.score = max(0, self.score - 10)

    def get_critical_issues(self) -> List[ValidationIssue]:
        """获取严重问题"""
        return [i for i in self.issues if i.severity == ValidationSeverity.CRITICAL]

    def get_warnings(self) -> List[ValidationIssue]:
        """获取警告"""
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def is_acceptable(self, threshold: float = 60.0) -> bool:
        """是否达到可接受标准"""
        return self.score >= threshold


class AnswerValidator:
    """答案验证器"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化验证器

        Args:
            config: 配置字典，包含验证阈值、规则等
        """
        self.config = config or {}
        self.score_threshold = self.config.get('score_threshold', 60.0)

        # 格式验证规则
        self.format_rules = {
            'required_sections': ['【直接回答】', '【详细说明】', '【数据来源】'],
            'max_direct_answer_length': self.config.get('max_direct_answer_length', 50),
            'min_detailed_explanation_length': self.config.get('min_detailed_explanation_length', 30),
        }

        # 内容验证规则
        self.content_rules = {
            'forbidden_phrases': [
                '不知道', '不清楚', '无法回答', '不能确定',
                '可能', '也许', '大概', '估计'
            ],
            'require_data_source': True,
            'require_evidence': True,
        }

        # 约束验证器（将在集成时注入）
        self.constraint_validator = None

        # Phase 2: 新增验证规则
        self.list_validator = None  # 列表完整性验证器
        self.time_period_validator = None  # 时间周期验证器

    def validate(
        self,
        answer: str,
        question: str,
        context: str = "",
        constraints: List[Any] = None
    ) -> ValidationResult:
        """
        执行完整验证

        Args:
            answer: 待验证的答案
            question: 用户问题
            context: 检索上下文
            constraints: 约束条件列表

        Returns:
            验证结果
        """
        result = ValidationResult(is_valid=True, score=100.0)

        # 1. 格式验证
        self._validate_format(answer, result)

        # 2. 内容验证
        self._validate_content(answer, question, result)

        # 3. 约束验证
        if constraints:
            self._validate_constraints(answer, question, constraints, result)

        # 4. 逻辑一致性验证
        self._validate_consistency(answer, question, context, result)

        # 5. 数据来源验证
        self._validate_data_sources(answer, result)

        # Phase 2: 6. 列表完整性验证（禁用以提升性能）
        # if context:
        #     self._validate_list_completeness(answer, question, context, result)

        # Phase 2: 7. 时间周期准确性验证（禁用以提升性能）
        # if context:
        #     self._validate_time_period_accuracy(answer, context, result)

        # 判断是否通过
        result.is_valid = result.is_acceptable(self.score_threshold)

        logger.info(f"验证完成: 得分={result.score:.1f}, 问题数={len(result.issues)}")

        return result

    def _validate_format(self, answer: str, result: ValidationResult):
        """验证答案格式"""
        # 检查必需的章节
        for section in self.format_rules['required_sections']:
            if section not in answer:
                result.add_issue(ValidationIssue(
                    issue_type="format",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"缺少必需的章节: {section}",
                    suggestion=f"请添加{section}章节"
                ))

        # 检查【直接回答】长度
        direct_match = re.search(r'【直接回答】\s*([^\【\n]*)', answer)
        if direct_match:
            direct_content = direct_match.group(1).strip()
            if len(direct_content) > self.format_rules['max_direct_answer_length']:
                result.add_issue(ValidationIssue(
                    issue_type="format",
                    severity=ValidationSeverity.WARNING,
                    message=f"【直接回答】过长 ({len(direct_content)}字符)",
                    suggestion=f"建议控制在{self.format_rules['max_direct_answer_length']}字符以内",
                    location="【直接回答】"
                ))

        # 检查【详细说明】长度
        detail_match = re.search(r'【详细说明】\s*([^\【]*?)(?=【数据来源】|$)', answer, re.DOTALL)
        if detail_match:
            detail_content = detail_match.group(1).strip()
            if len(detail_content) < self.format_rules['min_detailed_explanation_length']:
                result.add_issue(ValidationIssue(
                    issue_type="format",
                    severity=ValidationSeverity.WARNING,
                    message=f"【详细说明】过短 ({len(detail_content)}字符)",
                    suggestion=f"建议至少{self.format_rules['min_detailed_explanation_length']}字符",
                    location="【详细说明】"
                ))

        # 检查【数据来源】中是否有嵌套格式
        source_match = re.search(r'【数据来源】\s*(.*)', answer, re.DOTALL)
        if source_match:
            source_content = source_match.group(1)
            if re.search(r'【[^】]+】', source_content):
                result.add_issue(ValidationIssue(
                    issue_type="format",
                    severity=ValidationSeverity.CRITICAL,
                    message="【数据来源】中包含嵌套的格式标记",
                    suggestion="【数据来源】中只需列出文档名称，不要嵌套其他格式标记",
                    location="【数据来源】"
                ))

    def _validate_content(self, answer: str, question: str, result: ValidationResult):
        """验证答案内容"""
        answer_lower = answer.lower()

        # 检查是否包含禁止的模糊表述
        for phrase in self.content_rules['forbidden_phrases']:
            if phrase in answer:
                # 但如果【数据来源】中有文档信息，可能说明真的找不到
                has_sources = '【数据来源】' in answer and re.search(
                    r'【数据来源】.*?(?:文档|资料|文件)', answer, re.DOTALL
                )

                if not has_sources:
                    result.add_issue(ValidationIssue(
                        issue_type="content",
                        severity=ValidationSeverity.WARNING,
                        message=f"使用了不确定的表述: '{phrase}'",
                        suggestion="请根据检索到的资料给出明确答案"
                    ))

        # Phase 2: 增强的重复率检查
        direct_match = re.search(r'【直接回答】\s*([^\【\n]*)', answer)
        detail_match = re.search(r'【详细说明】\s*([^\【]*?)(?=【数据来源】|$)', answer, re.DOTALL)

        if direct_match and detail_match:
            direct_content = direct_match.group(1).strip()
            detail_content = detail_match.group(1).strip()

            # 计算精确的重复率
            repetition_ratio = self._calculate_repetition_ratio(direct_content, detail_content)

            # 获取配置的阈值
            max_repetition_ratio = self.config.get('max_repetition_ratio', 0.3)

            if repetition_ratio > max_repetition_ratio:
                result.add_issue(ValidationIssue(
                    issue_type="content",
                    severity=ValidationSeverity.WARNING,
                    message=f"【直接回答】与【详细说明】重复率过高 ({repetition_ratio:.0%})",
                    suggestion=f"【直接回答】应简洁概括结论，【详细说明】应展开说明具体数据和推理过程。当前重复率为{repetition_ratio:.0%}，建议控制在{max_repetition_ratio:.0%}以下。",
                    location="【直接回答】和【详细说明】"
                ))

    def _calculate_repetition_ratio(self, direct: str, detail: str) -> float:
        """
        计算【直接回答】在【详细说明】中的重复率（Phase 2 新增）

        Returns:
            重复率 (0.0 - 1.0)
        """
        if not direct or not detail:
            return 0.0

        # 移除标点符号和空格进行比较
        direct_clean = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', direct)
        detail_clean = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', detail)

        if not detail_clean:
            return 0.0

        # 计算直接回答的内容有多少出现在详细说明中
        matched_chars = 0
        for char in direct_clean:
            if char in detail_clean:
                matched_chars += 1

        ratio = matched_chars / len(direct_clean) if direct_clean else 0
        return min(ratio, 1.0)  # 确保不超过1

    def _validate_constraints(
        self,
        answer: str,
        question: str,
        constraints: List[Any],
        result: ValidationResult
    ):
        """验证约束条件"""
        if self.constraint_validator:
            is_valid, violations = self.constraint_validator(
                answer, question, constraints
            )
            if not is_valid:
                for violation in violations:
                    result.add_issue(ValidationIssue(
                        issue_type="constraint",
                        severity=ValidationSeverity.CRITICAL,
                        message=violation
                    ))
        else:
            # 简单的约束验证
            answer_lower = answer.lower()
            question_lower = question.lower()

            for constraint in constraints:
                if hasattr(constraint, 'condition') and hasattr(constraint, 'requirement'):
                    condition = constraint.condition.lower()
                    requirement = constraint.requirement.lower()

                    # 检查是否违反了约束
                    if condition in question_lower:
                        # 对于"仅限"类约束
                        if '仅限' in str(constraint):
                            # 如果答案说可以但没有确认满足条件
                            if any(kw in answer_lower for kw in ['可以', '支持', '能够']):
                                if not self._check_condition_mentioned(answer_lower, condition):
                                    result.add_issue(ValidationIssue(
                                        issue_type="constraint",
                                        severity=ValidationSeverity.CRITICAL,
                                        message=f"可能违反约束: {constraint.condition} {constraint.requirement}",
                                        suggestion=f"请确认是否满足{constraint.condition}"
                                    ))

    def _check_condition_mentioned(self, answer: str, condition: str) -> bool:
        """检查答案中是否提到了满足条件"""
        condition_met_keywords = ['满足', '符合', '达到', '具备', '是']
        return any(kw in answer for kw in condition_met_keywords)

    def _validate_consistency(
        self,
        answer: str,
        question: str,
        context: str,
        result: ValidationResult
    ):
        """验证逻辑一致性"""
        # 检查答案与问题是否相关
        question_keywords = re.findall(r'[\u4e00-\u9fa5]{2,}', question)
        if question_keywords:
            keyword_count = sum(1 for kw in question_keywords[:5] if kw in answer)
            if keyword_count < len(question_keywords[:5]) // 3:
                result.add_issue(ValidationIssue(
                    issue_type="consistency",
                    severity=ValidationSeverity.WARNING,
                    message="答案可能偏离问题主题",
                    suggestion="请确保答案直接回应问题"
                ))

    def _validate_data_sources(self, answer: str, result: ValidationResult):
        """验证数据来源"""
        source_match = re.search(r'【数据来源】\s*(.*)', answer, re.DOTALL)
        if not source_match or not source_match.group(1).strip():
            result.add_issue(ValidationIssue(
                issue_type="data_source",
                severity=ValidationSeverity.CRITICAL,
                message="缺少数据来源",
                suggestion="请在【数据来源】中列出参考的文档名称"
            ))

    # ========== Phase 2 新增验证方法 ==========

    def _validate_list_completeness(
        self,
        answer: str,
        question: str,
        context: str,
        result: ValidationResult
    ):
        """
        验证列表完整性（Phase 2 新增）

        检查答案是否遗漏了列表中的重要项目
        """
        # 从上下文中提取列表
        lists = self._extract_lists_from_context(context)

        if not lists:
            return

        # 检查问题是否与列表相关
        question_lower = question.lower()
        list_related_keywords = ['哪些', '包括', '有什么', '包含', '有哪些', '有什么业务', '有什么产品']

        if not any(kw in question_lower for kw in list_related_keywords):
            return

        # 检查每个列表
        answer_lower = answer.lower()

        for list_title, list_items in lists.items():
            if len(list_items) < 2:  # 至少2个项目才算列表
                continue

            missing_items = []
            for item in list_items:
                if item.lower() not in answer_lower and len(item) >= 3:  # 忽略太短的词
                    missing_items.append(item)

            if missing_items:
                # 计算缺失比例
                missing_ratio = len(missing_items) / len(list_items)

                if missing_ratio > 0.3:  # 超过30%缺失
                    result.add_issue(ValidationIssue(
                        issue_type="list_completeness",
                        severity=ValidationSeverity.CRITICAL if missing_ratio > 0.5 else ValidationSeverity.WARNING,
                        message=f"答案可能遗漏了列表项: {', '.join(missing_items[:3])}{'...' if len(missing_items) > 3 else ''}",
                        suggestion=f"根据文档，{list_title}包括：{', '.join(list_items)}。请确保答案完整列出所有项目。",
                        location=f"{list_title}列表"
                    ))

    def _extract_lists_from_context(self, context: str) -> Dict[str, List[str]]:
        """
        从上下文中提取列表（Phase 2 新增）

        Returns:
            字典，键为列表标题，值为项目列表
        """
        lists = {}

        # 模式1: "指定XXX包括：A、B、C"
        pattern1 = r'指定([^。：]+?)[：:]\s*([^。\n]*?[、,][^。\n]*?(?:[、,][^。\n]*?)*)(?:[。。]|$)'
        matches1 = re.finditer(pattern1, context)
        for match in matches1:
            title = match.group(1).strip()
            content = match.group(2).strip()
            items = self._parse_list_items(content)
            if len(items) >= 2:
                lists[title] = items

        # 模式2: "包括：A、B、C"
        pattern2 = r'([^。]{2,15}?(?:业务|产品|项目))包括[：:]\s*([^。\n]*?[、,][^。\n]*?(?:[、,][^。\n]*?)*)(?:[。。]|$)'
        matches2 = re.finditer(pattern2, context)
        for match in matches2:
            title = match.group(1).strip()
            content = match.group(2).strip()
            items = self._parse_list_items(content)
            if len(items) >= 2:
                lists[title] = items

        # 模式3: "可选择A、B、C"
        pattern3 = r'选择(?:其中)?一个(?:办理|使用)[：:]\s*([^。\n]*?[、,][^。\n]*?(?:[、,][^。\n]*?)*)(?:[。。]|$)'
        matches3 = re.finditer(pattern3, context)
        for match in matches3:
            title = "可选项目"
            content = match.group(1).strip()
            items = self._parse_list_items(content)
            if len(items) >= 2:
                lists[title] = items

        return lists

    def _parse_list_items(self, content: str) -> List[str]:
        """解析列表内容（Phase 2 新增）"""
        items = []

        # 尝试多种分隔符
        separators = ['、', ',', ';', '\\n']

        for sep in separators:
            if sep in content:
                items = [item.strip() for item in content.split(sep)]
                break

        # 过滤空项和过短项
        items = [item for item in items if item and len(item) >= 2]

        return items

    def _validate_time_period_accuracy(
        self,
        answer: str,
        context: str,
        result: ValidationResult
    ):
        """
        验证时间周期的准确性（Phase 2 新增）

        检查答案中的时间周期（如 T+3至T+7）是否与文档一致
        """
        # 从上下文中提取时间周期
        context_periods = self._extract_time_periods(context)

        # 从答案中提取时间周期
        answer_periods = self._extract_time_periods(answer)

        # 比较时间周期
        for ctx_period in context_periods:
            for ans_period in answer_periods:
                if ctx_period['type'] == ans_period['type']:
                    # 检查是否一致
                    is_accurate, error_msg = self._compare_time_periods(ctx_period, ans_period)
                    if not is_accurate:
                        result.add_issue(ValidationIssue(
                            issue_type="time_period_accuracy",
                            severity=ValidationSeverity.CRITICAL,
                            message=error_msg,
                            suggestion=f"请核对文档中的正确时间周期: {ctx_period['original']}",
                            location=f"时间周期: {ans_period['original']}"
                        ))

    def _extract_time_periods(self, text: str) -> List[Dict[str, Any]]:
        """提取文本中的时间周期（Phase 2 新增）"""
        periods = []

        # 模式1: T+n 至 T+m
        pattern1 = r'T\+(\d+)\s*至\s*T\+(\d+)'
        matches1 = re.finditer(pattern1, text)
        for match in matches1:
            periods.append({
                'type': 't_range',
                'start': int(match.group(1)),
                'end': int(match.group(2)),
                'original': match.group(0)
            })

        # 模式2: T+n月
        pattern2 = r'T\+(\d+)月'
        matches2 = re.finditer(pattern2, text)
        for match in matches2:
            periods.append({
                'type': 't_point',
                'value': int(match.group(1)),
                'original': match.group(0)
            })

        # 模式3: 连续N个月
        pattern3 = r'连续\s*(\d+)\s*个月'
        matches3 = re.finditer(pattern3, text)
        for match in matches3:
            periods.append({
                'type': 'consecutive_months',
                'value': int(match.group(1)),
                'original': match.group(0)
            })

        # 模式4: 各发放X%
        pattern4 = r'各\s*发放\s*(\d+)%'
        matches4 = re.finditer(pattern4, text)
        for match in matches4:
            periods.append({
                'type': 'percentage_each',
                'value': int(match.group(1)),
                'original': match.group(0)
            })

        return periods

    def _compare_time_periods(
        self,
        context_period: Dict[str, Any],
        answer_period: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """比较两个时间周期是否一致（Phase 2 新增）"""
        if context_period['type'] == 't_range' and answer_period['type'] == 't_range':
            if (context_period['start'] != answer_period['start'] or
                context_period['end'] != answer_period['end']):
                return False, (f"时间周期错误: 答案为T+{answer_period['start']}至T+{answer_period['end']}，"
                             f"应为T+{context_period['start']}至T+{context_period['end']}")

        elif context_period['type'] == 'consecutive_months' and answer_period['type'] == 'consecutive_months':
            if context_period['value'] != answer_period['value']:
                return False, (f"连续月数错误: 答案为{answer_period['value']}个月，"
                             f"应为{context_period['value']}个月")

        elif context_period['type'] == 'percentage_each' and answer_period['type'] == 'percentage_each':
            if context_period['value'] != answer_period['value']:
                return False, (f"发放比例错误: 答案为各发放{answer_period['value']}%，"
                             f"应为各发放{context_period['value']}%")

        return True, ""

    # ======================================

    def format_validation_result(self, result: ValidationResult) -> str:
        """格式化验证结果"""
        lines = [f"## 验证结果 (得分: {result.score:.0f}/100)"]

        if result.is_valid:
            lines.append("✅ 验证通过")
        else:
            lines.append("❌ 验证未通过")

        if result.issues:
            lines.append("\n### 发现的问题:")

            # 严重问题
            critical = result.get_critical_issues()
            if critical:
                lines.append("\n**严重问题:**")
                for issue in critical:
                    lines.append(f"- [{issue.issue_type}] {issue.message}")
                    if issue.suggestion:
                        lines.append(f"  建议: {issue.suggestion}")

            # 警告
            warnings = result.get_warnings()
            if warnings:
                lines.append("\n**警告:**")
                for issue in warnings:
                    lines.append(f"- [{issue.issue_type}] {issue.message}")
                    if issue.suggestion:
                        lines.append(f"  建议: {issue.suggestion}")

        return "\n".join(lines)

    def should_regenerate(self, result: ValidationResult) -> Tuple[bool, str]:
        """
        判断是否需要重新生成

        Returns:
            (是否需要重新生成, 原因说明)
        """
        # 如果有严重问题，需要重新生成
        if result.get_critical_issues():
            return True, "存在严重格式或内容问题，需要重新生成"

        # 如果得分低于阈值，需要重新生成
        if result.score < self.score_threshold:
            return True, f"得分({result.score:.0f})低于阈值({self.score_threshold:.0f})"

        return False, ""


class ConstraintValidator:
    """约束条件验证器"""

    def __init__(self):
        self.violation_patterns = {
            'exclusive': [
                r'可以.*?(?:办理|使用|享受)'  # 对于"仅限"类，检查是否错误地说"可以"
            ],
            'exclusion': [
                r'(?:包含|支持|可以)'  # 对于"排除"类，检查是否错误地包含
            ]
        }

    def validate(
        self,
        answer: str,
        question: str,
        constraints: List[Any]
    ) -> Tuple[bool, List[str]]:
        """
        验证答案是否违反约束

        Returns:
            (是否通过, 违反列表)
        """
        violations = []

        for constraint in constraints:
            if hasattr(constraint, 'constraint_type'):
                violation = self._check_constraint(answer, question, constraint)
                if violation:
                    violations.append(violation)

        return len(violations) == 0, violations

    def _check_constraint(
        self,
        answer: str,
        question: str,
        constraint: Any
    ) -> Optional[str]:
        """检查单个约束"""
        answer_lower = answer.lower()
        question_lower = question.lower()

        condition = constraint.condition.lower() if hasattr(constraint, 'condition') else ""
        requirement = constraint.requirement.lower() if hasattr(constraint, 'requirement') else ""
        constraint_type = constraint.constraint_type if hasattr(constraint, 'constraint_type') else ""

        # 条件在问题中
        condition_in_question = condition in question_lower

        if constraint_type == "exclusive":
            # "仅限"类约束
            if condition_in_question:
                # 检查是否错误地说"可以"
                if any(kw in answer_lower for kw in ['可以', '支持', '能够', '允许']):
                    # 检查是否确认满足条件
                    if not self._condition_confirmed(answer_lower, condition):
                        return f"违反约束: {constraint.condition} {constraint.requirement}"

        elif constraint_type == "exclusion":
            # 排除类约束
            if requirement in answer_lower:
                return f"违反排除约束: 不应包含 {constraint.requirement}"

        return None

    def _condition_confirmed(self, answer: str, condition: str) -> bool:
        """检查答案是否确认满足条件"""
        confirmation_keywords = ['满足', '符合', '达到', '具备', '是']
        return any(kw in answer for kw in confirmation_keywords)


# 全局实例
_answer_validator = None


def get_answer_validator(config: Dict[str, Any] = None) -> AnswerValidator:
    """获取答案验证器实例"""
    global _answer_validator
    if _answer_validator is None:
        _answer_validator = AnswerValidator(config or {})
    return _answer_validator


def get_constraint_validator() -> ConstraintValidator:
    """获取约束验证器实例"""
    return ConstraintValidator()


if __name__ == "__main__":
    # 测试代码
    validator = AnswerValidator()

    # 测试答案
    test_answer = """
【直接回答】29元潮玩青春卡月租29元，包含30GB定向流量。

【详细说明】29元潮玩青春卡月租29元，包含30GB定向流量。套外流量按标准资费收取。

【数据来源】套餐资费表
"""

    test_question = "29元潮玩青春卡多少钱？"

    result = validator.validate(test_answer, test_question)
    print(validator.format_validation_result(result))

# -*- coding: utf-8 -*-
"""
持续学习模块

收集用户反馈、分析问题模式、支持模型优化
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """反馈类型"""
    THUMBS_UP = "thumbs_up"       # 点赞
    THUMBS_DOWN = "thumbs_down"   # 点踩
    CORRECTION = "correction"     # 纠正
    COMMENT = "comment"           # 评论
    REPORT_ISSUE = "report_issue" # 问题报告


class IssueCategory(Enum):
    """问题类别"""
    FORMAT_ERROR = "format_error"         # 格式错误
    WRONG_ANSWER = "wrong_answer"         # 答案错误
    MISSING_INFO = "missing_info"         # 信息缺失
    CONSTRAINT_VIOLATION = "violation"    # 违反约束
    UNCLEAR_ANSWER = "unclear"            # 答案不清晰
    OTHER = "other"                       # 其他


@dataclass
class Feedback:
    """用户反馈"""
    session_id: str  # 会话ID
    question: str  # 用户问题
    answer: str  # 系统答案
    feedback_type: FeedbackType  # 反馈类型
    issue_category: Optional[IssueCategory] = None  # 问题类别
    correction: Optional[str] = None  # 纠正内容
    comment: Optional[str] = None  # 评论
    rating: Optional[int] = None  # 评分(1-5)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据


@dataclass
class AnalysisResult:
    """分析结果"""
    total_feedbacks: int
    accuracy_rate: float
    common_issues: List[Tuple[IssueCategory, int]]
    problematic_questions: List[Tuple[str, int]]  # (question, error_count)
    improvement_suggestions: List[str]


class ContinuousLearner:
    """持续学习器"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化持续学习器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)

        # 反馈存储路径
        storage_path = self.config.get('feedback_collection', {}).get(
            'storage_path', 'data/feedback.json'
        )
        self.storage_path = os.path.join(os.path.dirname(__file__), '..', '..', storage_path)

        # 确保目录存在
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

        # 反重训练阈值
        self.min_feedback_count = self.config.get('retrain_threshold', {}).get(
            'min_feedback_count', 100
        )
        self.min_accuracy_drop = self.config.get('retrain_threshold', {}).get(
            'min_accuracy_drop', 0.05
        )

        # 加载已有反馈
        self.feedbacks: List[Feedback] = self._load_feedbacks()

    def add_feedback(self, feedback: Feedback) -> bool:
        """
        添加反馈

        Args:
            feedback: 反馈对象

        Returns:
            是否成功
        """
        try:
            self.feedbacks.append(feedback)
            self._save_feedbacks()
            logger.info(f"收到反馈: {feedback.feedback_type.value}")
            return True
        except Exception as e:
            logger.error(f"保存反馈失败: {e}")
            return False

    def add_simple_feedback(
        self,
        session_id: str,
        question: str,
        answer: str,
        is_positive: bool,
        comment: str = None
    ) -> bool:
        """
        添加简单反馈（点赞/点踩）

        Args:
            session_id: 会话ID
            question: 问题
            answer: 答案
            is_positive: 是否正面反馈
            comment: 可选评论

        Returns:
            是否成功
        """
        feedback = Feedback(
            session_id=session_id,
            question=question,
            answer=answer,
            feedback_type=FeedbackType.THUMBS_UP if is_positive else FeedbackType.THUMBS_DOWN,
            comment=comment
        )
        return self.add_feedback(feedback)

    def add_correction(
        self,
        session_id: str,
        question: str,
        answer: str,
        correction: str,
        issue_category: IssueCategory = None
    ) -> bool:
        """
        添加纠正反馈

        Args:
            session_id: 会话ID
            question: 问题
            answer: 原答案
            correction: 正确答案
            issue_category: 问题类别

        Returns:
            是否成功
        """
        feedback = Feedback(
            session_id=session_id,
            question=question,
            answer=answer,
            feedback_type=FeedbackType.CORRECTION,
            correction=correction,
            issue_category=issue_category
        )
        return self.add_feedback(feedback)

    def _load_feedbacks(self) -> List[Feedback]:
        """加载已保存的反馈"""
        if not os.path.exists(self.storage_path):
            return []

        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return [self._dict_to_feedback(item) for item in data]
        except Exception as e:
            logger.error(f"加载反馈失败: {e}")
            return []

    def _save_feedbacks(self) -> None:
        """保存反馈到文件"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                # 转换为字典，处理枚举类型
                data = []
                for fb in self.feedbacks:
                    fb_dict = asdict(fb)
                    # 转换枚举为字符串
                    if isinstance(fb_dict.get('feedback_type'), FeedbackType):
                        fb_dict['feedback_type'] = fb_dict['feedback_type'].value
                    if isinstance(fb_dict.get('issue_category'), IssueCategory):
                        fb_dict['issue_category'] = fb_dict['issue_category'].value
                    data.append(fb_dict)
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存反馈失败: {e}")

    def _dict_to_feedback(self, data: Dict) -> Feedback:
        """将字典转换为Feedback对象"""
        # 转换字符串为枚举
        feedback_type = data.get('feedback_type')
        if isinstance(feedback_type, str):
            try:
                data['feedback_type'] = FeedbackType(feedback_type)
            except ValueError:
                data['feedback_type'] = FeedbackType.COMMENT

        issue_category = data.get('issue_category')
        if isinstance(issue_category, str):
            try:
                data['issue_category'] = IssueCategory(issue_category)
            except ValueError:
                data['issue_category'] = None
        elif issue_category is None:
            data['issue_category'] = None

        return Feedback(**data)

    def analyze_feedbacks(self) -> AnalysisResult:
        """
        分析反馈数据

        Returns:
            分析结果
        """
        if not self.feedbacks:
            return AnalysisResult(
                total_feedbacks=0,
                accuracy_rate=0.0,
                common_issues=[],
                problematic_questions=[],
                improvement_suggestions=["暂无足够数据进行分析"]
            )

        # 统计总数
        total = len(self.feedbacks)

        # 统计正面/负面反馈
        positive_count = sum(
            1 for fb in self.feedbacks
            if fb.feedback_type in [FeedbackType.THUMBS_UP]
        )
        accuracy_rate = positive_count / total if total > 0 else 0

        # 统计问题类别
        issue_counter = Counter()
        for fb in self.feedbacks:
            if fb.issue_category:
                issue_counter[fb.issue_category] += 1
            elif fb.feedback_type == FeedbackType.THUMBS_DOWN:
                issue_counter[IssueCategory.OTHER] += 1

        common_issues = issue_counter.most_common(5)

        # 找出高频错误问题
        question_errors = defaultdict(int)
        for fb in self.feedbacks:
            if fb.feedback_type in [FeedbackType.THUMBS_DOWN, FeedbackType.CORRECTION, FeedbackType.REPORT_ISSUE]:
                question_errors[fb.question] += 1

        problematic_questions = sorted(
            question_errors.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # 生成改进建议
        improvement_suggestions = self._generate_suggestions(
            accuracy_rate, common_issues, problematic_questions
        )

        return AnalysisResult(
            total_feedbacks=total,
            accuracy_rate=accuracy_rate,
            common_issues=common_issues,
            problematic_questions=problematic_questions,
            improvement_suggestions=improvement_suggestions
        )

    def _generate_suggestions(
        self,
        accuracy_rate: float,
        common_issues: List[Tuple[IssueCategory, int]],
        problematic_questions: List[Tuple[str, int]]
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 基于准确率的建议
        if accuracy_rate < 0.7:
            suggestions.append(f"准确率较低({accuracy_rate:.1%})，建议检查检索质量和模型生成能力")
        elif accuracy_rate < 0.85:
            suggestions.append(f"准确率有待提高({accuracy_rate:.1%})，建议加强约束条件验证")

        # 基于问题类型的建议
        issue_types = dict(common_issues)
        if issue_types.get(IssueCategory.FORMAT_ERROR, 0) > 5:
            suggestions.append("格式错误较多，建议强化格式验证机制")

        if issue_types.get(IssueCategory.WRONG_ANSWER, 0) > 5:
            suggestions.append("答案错误较多，建议改进检索策略和提示词设计")

        if issue_types.get(IssueCategory.CONSTRAINT_VIOLATION, 0) > 3:
            suggestions.append("约束违反较多，建议加强约束条件提取和验证")

        if issue_types.get(IssueCategory.UNCLEAR_ANSWER, 0) > 5:
            suggestions.append("答案不清晰问题较多，建议优化提示词，要求更明确的回答")

        return suggestions

    def should_retrain(self) -> Tuple[bool, str]:
        """
        判断是否需要重新训练模型

        Returns:
            (是否需要, 原因说明)
        """
        if not self.enabled:
            return False, "持续学习未启用"

        analysis = self.analyze_feedbacks()

        # 检查反馈数量
        if analysis.total_feedbacks < self.min_feedback_count:
            return False, f"反馈数量不足 ({analysis.total_feedbacks}/{self.min_feedback_count})"

        # 检查准确率下降
        if analysis.accuracy_rate < (1 - self.min_accuracy_drop):
            return True, f"准确率低于阈值 ({analysis.accuracy_rate:.1%} < {1-self.min_accuracy_drop:.1%})"

        return False, "暂无必要重新训练"

    def get_training_data(self) -> List[Dict[str, Any]]:
        """
        获取用于训练的数据

        Returns:
            训练数据列表
        """
        training_data = []

        for fb in self.feedbacks:
            # 只使用纠正反馈和正面反馈
            if fb.feedback_type == FeedbackType.CORRECTION:
                training_data.append({
                    'question': fb.question,
                    'answer': fb.correction,
                    'type': 'correction',
                    'original_answer': fb.answer
                })
            elif fb.feedback_type == FeedbackType.THUMBS_UP:
                training_data.append({
                    'question': fb.question,
                    'answer': fb.answer,
                    'type': 'positive'
                })

        return training_data

    def export_analysis_report(self) -> str:
        """
        导出分析报告

        Returns:
            报告文本
        """
        analysis = self.analyze_feedbacks()

        lines = [
            "# 持续学习分析报告",
            f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "\n## 基本统计",
            f"- 总反馈数: {analysis.total_feedbacks}",
            f"- 准确率: {analysis.accuracy_rate:.1%}",
        ]

        if analysis.common_issues:
            lines.append("\n## 常见问题类型")
            for issue, count in analysis.common_issues:
                lines.append(f"- {issue.value}: {count}次")

        if analysis.problematic_questions:
            lines.append("\n## 高频错误问题")
            for question, count in analysis.problematic_questions:
                lines.append(f"- ({count}次) {question[:50]}...")

        if analysis.improvement_suggestions:
            lines.append("\n## 改进建议")
            for suggestion in analysis.improvement_suggestions:
                lines.append(f"- {suggestion}")

        retrain, reason = self.should_retrain()
        lines.append(f"\n## 重新训练评估")
        lines.append(f"- 状态: {'需要' if retrain else '暂不需要'}")
        lines.append(f"- 说明: {reason}")

        return "\n".join(lines)


class FeedbackCollector:
    """反馈收集器（供API使用）"""

    def __init__(self, learner: ContinuousLearner = None):
        self.learner = learner or ContinuousLearner()

    def collect(
        self,
        session_id: str,
        question: str,
        answer: str,
        feedback_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        收集反馈

        Args:
            session_id: 会话ID
            question: 问题
            answer: 答案
            feedback_data: 反馈数据，包含:
                - type: 反馈类型 (thumbs_up, thumbs_down, correction, comment, report_issue)
                - rating: 评分 (可选)
                - comment: 评论 (可选)
                - correction: 纠正内容 (可选)
                - issue_category: 问题类别 (可选)

        Returns:
            收集结果
        """
        try:
            feedback_type = FeedbackType(feedback_data.get('type', 'comment'))

            feedback = Feedback(
                session_id=session_id,
                question=question,
                answer=answer,
                feedback_type=feedback_type,
                rating=feedback_data.get('rating'),
                comment=feedback_data.get('comment'),
                correction=feedback_data.get('correction'),
                issue_category=IssueCategory(feedback_data['issue_category']) if feedback_data.get('issue_category') else None,
                metadata=feedback_data.get('metadata', {})
            )

            success = self.learner.add_feedback(feedback)

            return {
                'success': success,
                'message': '反馈已收集' if success else '反馈收集失败'
            }
        except Exception as e:
            logger.error(f"收集反馈时出错: {e}")
            return {
                'success': False,
                'message': f'收集反馈时出错: {str(e)}'
            }


# 全局实例
_continuous_learner = None


def get_continuous_learner(config: Dict[str, Any] = None) -> ContinuousLearner:
    """获取持续学习器实例"""
    global _continuous_learner
    if _continuous_learner is None:
        _continuous_learner = ContinuousLearner(config)
    return _continuous_learner


def get_feedback_collector() -> FeedbackCollector:
    """获取反馈收集器实例"""
    return FeedbackCollector(get_continuous_learner())


if __name__ == "__main__":
    # 测试代码
    learner = ContinuousLearner()

    # 模拟添加一些反馈
    learner.add_simple_feedback(
        session_id="test_001",
        question="29元潮玩青春卡多少钱？",
        answer="【直接回答】29元\n【详细说明】29元潮玩青春卡月租29元。\n【数据来源】套餐资费表",
        is_positive=True
    )

    learner.add_correction(
        session_id="test_002",
        question="万能副卡多少钱？",
        answer="【直接回答】10元\n【详细说明】万能副卡月费10元。\n【数据来源】资费表",
        correction="万能副卡月费0元，但仅限59元及以上套餐办理",
        issue_category=IssueCategory.CONSTRAINT_VIOLATION
    )

    learner.add_simple_feedback(
        session_id="test_003",
        question="校园渠道可以办理什么？",
        answer="【直接回答】不清楚\n【详细说明】文档中未明确说明。\n【数据来源】无",
        is_positive=False
    )

    # 导出分析报告
    print(learner.export_analysis_report())

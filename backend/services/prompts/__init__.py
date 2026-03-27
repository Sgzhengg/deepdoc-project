"""
提示词模板系统

针对运营商渠道业务优化的提示词模板
"""

from .base import BasePromptTemplate, PromptBuilder, prompt_builder
from .simple_query import SimpleQueryPrompt
from .complex_query import ComplexQueryPrompt
from .follow_up import FollowUpPrompt
from .calculation import CalculationPromptTemplate

__all__ = [
    'BasePromptTemplate',
    'SimpleQueryPrompt',
    'ComplexQueryPrompt',
    'FollowUpPrompt',
    'CalculationPromptTemplate',
    'prompt_builder',
    'PromptBuilder',
]

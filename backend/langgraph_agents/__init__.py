"""
LangGraph Agents - DeepDoc多Agent系统
"""

from .state import AgentState, create_initial_state, state_to_dict

__version__ = "1.0.0"

__all__ = [
    "AgentState",
    "create_initial_state",
    "state_to_dict"
]

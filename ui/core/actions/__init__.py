"""
统一功能组件模块 — 提供 Action 注册和创建能力
"""
from .action_definition import ActionDefinition, ActionContext, ActionCategory
from .action_registry import ActionRegistry
from .action_factory import ActionFactory

__all__ = [
    'ActionDefinition',
    'ActionContext',
    'ActionCategory',
    'ActionRegistry',
    'ActionFactory',
]

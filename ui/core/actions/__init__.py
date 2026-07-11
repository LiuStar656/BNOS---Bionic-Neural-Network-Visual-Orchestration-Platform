"""
统一功能组件模块 — 提供 Action 注册和创建能力
"""

from __future__ import annotations

from .action_definition import ActionCategory, ActionContext, ActionDefinition
from .action_factory import ActionFactory
from .action_registry import ActionRegistry

__all__ = [
    "ActionDefinition",
    "ActionContext",
    "ActionCategory",
    "ActionRegistry",
    "ActionFactory",
]

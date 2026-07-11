"""
BNOS主窗口模块
包含主窗口的各个职责分离模块
"""

from __future__ import annotations

from .__main__ import BNOSMainWindow
from .actions import MainWindowActionsMixin
from .interaction import MainWindowInteractionMixin
from .ipc import MainWindowIPCMixin
from .lifecycle import MainWindowLifecycleMixin
from .node import MainWindowNodeControlMixin
from .panel import MainWindowPanelMixin
from .state import MainWindowStateMixin

__all__ = [
    "BNOSMainWindow",
    "MainWindowStateMixin",
    "MainWindowLifecycleMixin",
    "MainWindowActionsMixin",
    "MainWindowPanelMixin",
    "MainWindowIPCMixin",
    "MainWindowNodeControlMixin",
    "MainWindowInteractionMixin",
]

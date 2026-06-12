"""
BNOS主窗口模块
包含主窗口的各个职责分离模块
"""

from .state import MainWindowStateMixin
from .lifecycle import MainWindowLifecycleMixin
from .actions import MainWindowActionsMixin
from .panel import MainWindowPanelMixin
from .ipc import MainWindowIPCMixin
from .node import MainWindowNodeControlMixin
from .interaction import MainWindowInteractionMixin
from .__main__ import BNOSMainWindow

__all__ = [
    'BNOSMainWindow',
    'MainWindowStateMixin',
    'MainWindowLifecycleMixin',
    'MainWindowActionsMixin',
    'MainWindowPanelMixin',
    'MainWindowIPCMixin',
    'MainWindowNodeControlMixin',
    'MainWindowInteractionMixin',
]

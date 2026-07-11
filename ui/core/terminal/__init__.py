"""
终端模块 - 提供终端 Dock 功能
"""

from __future__ import annotations

from .terminal_dock import TerminalDock
from .terminal_process import TerminalProcess
from .terminal_widget import TerminalWidget

__all__ = ["TerminalDock", "TerminalWidget", "TerminalProcess"]

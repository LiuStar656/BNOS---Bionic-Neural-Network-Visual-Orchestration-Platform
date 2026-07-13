"""状态机模块 - 独立组件，零业务依赖。

提供通用 StateMachine 基类及各模块的专用状态机实现。
"""

from ui.core.state.base import StateMachine, Transition

__all__ = ["StateMachine", "Transition"]

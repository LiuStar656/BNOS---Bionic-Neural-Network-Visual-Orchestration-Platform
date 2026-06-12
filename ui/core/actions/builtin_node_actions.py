"""
内置节点操作功能定义（兼容重定向 — 所有 action 已迁移至 node/ 子包）

新路径：
    from ui.core.actions.node import register_node_actions
"""
import warnings

warnings.warn(
    "builtin_node_actions.py 已废弃，请改用 ui.core.actions.node",
    DeprecationWarning,
    stacklevel=2,
)

from ui.core.actions.node import register_node_actions  # noqa: F401,E402

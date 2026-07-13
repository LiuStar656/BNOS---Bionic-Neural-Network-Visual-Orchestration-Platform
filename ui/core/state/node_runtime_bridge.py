"""节点运行时状态机桥接。

提供 node_process.py 与 NodeRuntimeSM 之间的轻量兼容层。
不影响现有 node_info["status"] 字典读写，仅将状态转换委托到状态机。

用法:
    from ui.core.state.node_runtime_bridge import ensure_sm, transition_state

    sm = ensure_sm(node_info)                    # 获取或创建 SM
    is_ok = transition_state(node_info, "start") # 触发状态转换，同步 node_info["status"]
"""

from __future__ import annotations

from typing import Any

from ui.core.state.node_runtime import NodeRuntimeSM


def ensure_sm(node_info: dict[str, Any]) -> NodeRuntimeSM:
    """获取或创建节点信息字典中的状态机。"""
    if "_sm" not in node_info:
        node_name = node_info.get("path", "").rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
        node_info["_sm"] = NodeRuntimeSM(node_name)
    return node_info["_sm"]


def get_state(node_info: dict[str, Any]) -> str:
    """读取当前节点运行时状态（从状态机）。"""
    sm = node_info.get("_sm")
    if sm is not None:
        return sm.state
    return node_info.get("status", "stopped")


def transition_state(node_info: dict[str, Any], event: str) -> bool:
    """触发状态转换事件，成功后自动同步 node_info["status"]。

    Returns:
        True 表示转换成功，False 表示非法转换。
    """
    sm = ensure_sm(node_info)
    ok = sm.handle(event)
    if ok:
        node_info["status"] = sm.state
    return ok


def sync_status_to_dict(node_info: dict[str, Any]) -> None:
    """将状态机的当前状态同步到 node_info["status"]（兼容读取）。"""
    sm = node_info.get("_sm")
    if sm is not None:
        node_info["status"] = sm.state

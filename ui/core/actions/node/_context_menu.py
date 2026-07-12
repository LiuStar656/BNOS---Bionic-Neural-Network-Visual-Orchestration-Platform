"""节点右键菜单操作 — add_to_canvas / open_folder / view_log / edit_config / rename / delete / unmount"""
# ruff: noqa: T201 — diagnostic print() for rename tracing

from __future__ import annotations

from ..action_definition import ActionCategory, ActionContext, ActionDefinition
from ..action_registry import ActionRegistry


def register(main_window):
    """注册节点右键菜单（通过 panel extra 桥接）action"""

    _register_panel_action("node.add_to_canvas", "k_canvas_add_to", "add_node_to_canvas")
    _register_panel_action("node.open_folder", "k_open_dir", "open_node_folder")
    _register_panel_action("node.view_log", "k_view_log", "view_node_log")
    _register_panel_action("node.edit_config", "k_edit_config", "edit_node_config")
    _register_panel_action("node.rename", "k_node_rename", "rename_node")
    _register_panel_action("node.delete", "k_node_delete", "delete_node")
    _register_panel_action("node.unmount", "k_node_unmount", "_unmount_node")


def _register_panel_action(action_id: str, name_i18n: str, method: str):
    def execute(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get("panel")
        window = (ctx.extra or {}).get("window")
        canvas = (ctx.extra or {}).get("canvas")
        # 通过 canvas 间接获取 window（画布右键菜单场景）
        if not window and canvas and hasattr(canvas, "parent_window"):
            window = canvas.parent_window
        _pn = (
            f"{type(panel).__name__}({method}={'YES' if panel and hasattr(panel, method) else 'NO'})"
            if panel
            else "N/A"
        )
        _wn = (
            f"{type(window).__name__}({method}={'YES' if window and hasattr(window, method) else 'NO'})"
            if window
            else "N/A"
        )
        print(f"[ACTION][{method}] node={ctx.node_name} panel={_pn} window={_wn}")
        if ctx.node_name:
            if panel and hasattr(panel, method):
                print(f"[ACTION][{method}] → panel.{method}()")
                getattr(panel, method)(ctx.node_name)
                return True
            if window and hasattr(window, method):
                print(f"[ACTION][{method}] → window.{method}()")
                getattr(window, method)(ctx.node_name)
                return True
        print(f"[ACTION][{method}] FAILED: no valid handler")
        return False

    ActionRegistry.register(
        ActionDefinition(
            id=action_id, name_i18n=name_i18n, category=ActionCategory.NODE, execute_fn=execute, requires_node=True
        )
    )

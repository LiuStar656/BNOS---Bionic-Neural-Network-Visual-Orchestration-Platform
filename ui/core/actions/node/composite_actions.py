"""
ui/core/actions/node/composite_actions.py
┐̏合节点操作 — 压缩/解耦 action 注册。

通过 ActionRegistry 注册，canvas 右键菜单和节点列表均通过 Action 系统分发。
"""

from __future__ import annotations

from ..action_definition import ActionCategory, ActionContext, ActionDefinition
from ..action_registry import ActionRegistry


def register(main_window):
    """注册复合节点相关 action"""
    _register_compress(main_window)
    _register_decompress(main_window)


def _register_compress(main_window):
    """注册"压缩为复合节点" — 多选节点 → 复合节点"""

    def execute(ctx: ActionContext) -> bool:
        node_list = ctx.node_list
        if not node_list or len(node_list) < 2:
            return False

        from ui.core.i18n import t
        from ui.core.node.composite_node import CompositeNode
        from ui.core.utils.dialog_utils import themed_message

        canvas = ctx.extra.get("canvas") if ctx.extra else None
        if not canvas:
            return False

        project_path = getattr(main_window, "current_project_path", None)
        if not project_path:
            return False

        group_manager = None
        if hasattr(main_window, "node_list_panel") and main_window.node_list_panel:
            group_manager = main_window.node_list_panel.group_manager

        mgr = CompositeNode(project_path, canvas, group_manager)
        canvas._composite_manager = mgr

        ok, msg, comp_id = mgr.compress(node_list)
        if not ok:
            themed_message(None, t("k_title_error"), msg, "error")
            return False

        # 刷新节点列表
        if hasattr(main_window, "node_list_panel") and main_window.node_list_panel:
            main_window.node_list_panel.refresh()

        return True

    ActionRegistry.register(
        ActionDefinition(
            id="canvas.compress_to_composite",
            name_i18n="k_compress_to_composite",
            category=ActionCategory.CANVAS,
            execute_fn=execute,
            requires_node=True,
        )
    )


def _register_decompress(main_window):
    """注册"解耦复合节点" — 复合节点 → 独立节点"""

    def execute(ctx: ActionContext) -> bool:
        comp_id = ctx.extra.get("comp_id") if ctx.extra else None
        if not comp_id:
            return False

        from ui.core.i18n import t
        from ui.core.utils.dialog_utils import themed_message

        canvas = ctx.extra.get("canvas") if ctx.extra else None
        if not canvas:
            return False

        mgr = getattr(canvas, "_composite_manager", None)
        if not mgr:
            return False

        ok, msg = mgr.decompress(comp_id)
        if not ok:
            themed_message(None, t("k_title_error"), msg, "error")
            return False

        if hasattr(main_window, "node_list_panel") and main_window.node_list_panel:
            main_window.node_list_panel.refresh()

        return True

    ActionRegistry.register(
        ActionDefinition(
            id="canvas.decompress_composite",
            name_i18n="k_decompress_composite",
            category=ActionCategory.CANVAS,
            execute_fn=execute,
            requires_node=True,
        )
    )

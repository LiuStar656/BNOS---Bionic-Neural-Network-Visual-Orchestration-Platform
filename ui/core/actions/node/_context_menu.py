"""节点右键菜单操作 — add_to_canvas / open_folder / view_log / edit_config / rename / delete / unmount"""
from ..action_definition import ActionDefinition, ActionCategory, ActionContext
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
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.node_name:
            getattr(panel, method)(ctx.node_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id=action_id, name_i18n=name_i18n, category=ActionCategory.NODE,
        execute_fn=execute, requires_node=True))

"""分组操作 — 10 个 group.* action"""
from ..action_definition import ActionDefinition, ActionCategory, ActionContext
from ..action_registry import ActionRegistry


def register(main_window):
    """注册分组操作 action"""

    def _panel_action(action_id, name_i18n, method, kw="group_name"):
        def execute(ctx: ActionContext) -> bool:
            panel = (ctx.extra or {}).get('panel')
            arg = getattr(ctx, kw, None)
            if panel and arg:
                getattr(panel, method)(arg)
                return True
            return False
        ActionRegistry.register(ActionDefinition(
            id=action_id, name_i18n=name_i18n, category=ActionCategory.NODE, execute_fn=execute))

    _panel_action("group.create", "k_group_create", "create_node_group", kw="group_name")

    def _move_to(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.node_name and ctx.group_name:
            panel.move_node_to_group(ctx.node_name, ctx.group_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="group.move_to", name_i18n="k_group_move", category=ActionCategory.NODE, execute_fn=_move_to))

    _panel_action("group.batch_move_to", "k_group_move", "batch_move_nodes_to_group")
    _panel_action("group.batch_remove_from", "_k_group_remove_from", "batch_remove_nodes_from_group")

    def _remove_from(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.node_name:
            panel.remove_node_from_group(ctx.node_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="group.remove_from", name_i18n="_k_group_remove_from", category=ActionCategory.NODE, execute_fn=_remove_from))

    _panel_action("group.rename", "k_group_rename", "rename_group")
    _panel_action("group.delete", "k_group_delete", "delete_group")
    _panel_action("group.start", "_k_start_group_nodes", "start_group_nodes")
    _panel_action("group.stop", "_k_stop_group_nodes", "stop_group_nodes")
    _panel_action("group.toggle_expand", "k_group_expand_collapse", "toggle_group_expansion")

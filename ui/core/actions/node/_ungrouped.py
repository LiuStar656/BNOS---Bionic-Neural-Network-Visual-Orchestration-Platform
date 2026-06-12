"""未分组节点操作 — start / stop 未分组节点"""
from ..action_definition import ActionDefinition, ActionCategory, ActionContext
from ..action_registry import ActionRegistry


def register(main_window):
    """注册未分组节点 start/stop action"""

    def _panel_action(action_id, name_i18n, method):
        def execute(ctx: ActionContext) -> bool:
            panel = (ctx.extra or {}).get('panel')
            if panel:
                getattr(panel, method)()
                return True
            return False

        ActionRegistry.register(ActionDefinition(
            id=action_id, name_i18n=name_i18n, category=ActionCategory.NODE, execute_fn=execute))

    _panel_action("ungrouped.start", "_k_start_ungrouped", "start_ungrouped_nodes")
    _panel_action("ungrouped.stop", "_k_stop_ungrouped", "stop_ungrouped_nodes")

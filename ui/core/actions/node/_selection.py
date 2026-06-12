"""选择操作 — select_all / deselect_all"""
from ..action_definition import ActionDefinition, ActionCategory, ActionContext
from ..action_registry import ActionRegistry


def register(main_window):
    """注册全选/取消全选 action"""

    def _panel_action(method: str):
        def execute(ctx: ActionContext) -> bool:
            panel = (ctx.extra or {}).get('panel')
            if panel:
                getattr(panel, method)()
                return True
            return False
        return execute

    ActionRegistry.register(ActionDefinition(
        id="node.select_all", name_i18n="k_select_all", category=ActionCategory.NODE,
        execute_fn=_panel_action("select_all_nodes")))

    ActionRegistry.register(ActionDefinition(
        id="node.deselect_all", name_i18n="k_select_cancel", category=ActionCategory.NODE,
        execute_fn=_panel_action("deselect_all_nodes")))

"""IDE 集成操作 — open_vscode / open_trae_ide"""
from ..action_definition import ActionDefinition, ActionCategory, ActionContext
from ..action_registry import ActionRegistry


def register(main_window):
    """注册 IDE 打开 action"""

    def execute_node_open_vscode(ctx: ActionContext) -> bool:
        from ui.core.ide_scanner import ide_scanner
        node_name = (ctx.extra or {}).get('node_name', ctx.node_name or '')
        node_path = (ctx.extra or {}).get('node_path', '')
        if node_name and node_path:
            return ide_scanner.open_vscode_workspace(node_name, node_path)
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.open_vscode", name_i18n="k_open_vscode", category=ActionCategory.NODE,
        execute_fn=execute_node_open_vscode, requires_node=True))

    def execute_node_open_trae(ctx: ActionContext) -> bool:
        from ui.core.ide_scanner import ide_scanner
        node_path = (ctx.extra or {}).get('node_path', '')
        if node_path:
            return ide_scanner.open_in_trae(node_path)
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.open_trae_ide", name_i18n="_k_open_trae", category=ActionCategory.NODE,
        execute_fn=execute_node_open_trae, requires_node=True))

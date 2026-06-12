"""批量节点操作 — 5 个 batch_* action"""
from ..action_definition import ActionDefinition, ActionCategory, ActionContext
from ..action_registry import ActionRegistry


def register(main_window):
    """注册批量节点操作 action"""

    _register_batch("node.batch_add_to_canvas", "_k_add_n_to_canvas", "batch_add_nodes_to_canvas")
    _register_batch("node.batch_open_folders", "_k_open_n_dirs", "batch_open_node_folders")
    _register_batch("node.batch_view_logs", "_k_view_n_logs", "batch_view_node_logs")
    _register_batch("node.batch_edit_configs", "_k_edit_n_configs", "batch_edit_node_configs")
    _register_batch("node.batch_delete", "_k_delete_n_nodes", "batch_delete_nodes")


def _register_batch(action_id: str, name_i18n: str, method: str):
    def execute(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel:
            getattr(panel, method)()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id=action_id, name_i18n=name_i18n, category=ActionCategory.NODE, execute_fn=execute))

"""节点样式操作 — change_style / change_bg_color / change_border_color / change_text_color"""
from ..action_definition import ActionDefinition, ActionCategory, ActionContext
from ..action_registry import ActionRegistry


def register(main_window):
    """注册节点样式切换 action"""

    def execute_node_change_style(ctx: ActionContext) -> bool:
        node_item = (ctx.extra or {}).get('node_item') if ctx.extra else None
        style_key = (ctx.extra or {}).get('style_key') if ctx.extra else None
        canvas = (ctx.extra or {}).get('canvas') if ctx.extra else None
        if node_item and style_key and canvas:
            canvas._switch_node_style(style_key, node_item)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.change_style", name_i18n="k_node_style", category=ActionCategory.NODE,
        execute_fn=execute_node_change_style, requires_node=True))

    def _color_action(action_id: str, name_i18n: str, method: str):
        def execute(ctx: ActionContext) -> bool:
            node_item = (ctx.extra or {}).get('node_item') if ctx.extra else None
            canvas = (ctx.extra or {}).get('canvas') if ctx.extra else None
            if node_item and canvas:
                getattr(canvas, method)(node_item)
                return True
            return False
        ActionRegistry.register(ActionDefinition(
            id=action_id, name_i18n=name_i18n, category=ActionCategory.NODE,
            execute_fn=execute, requires_node=True))

    _color_action("node.change_bg_color", "k_node_bg_color", "change_node_background_color")
    _color_action("node.change_border_color", "k_node_border_color", "change_node_border_color")
    _color_action("node.change_text_color", "k_node_text_color", "change_node_text_color")

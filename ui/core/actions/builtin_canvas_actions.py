"""
内置画布操作功能定义
"""
from .action_definition import ActionDefinition, ActionCategory, ActionContext
from .action_registry import ActionRegistry


def register_canvas_actions(main_window):
    """注册画布相关功能"""
    
    ActionRegistry.register(ActionDefinition(
        id="canvas.clear_connections",
        name_i18n="k_canvas_clear_connections",
        category=ActionCategory.CANVAS,
        shortcut_id="clear_connections",
        description_i18n="k_canvas_clear_connections_desc",
        execute_fn=lambda ctx: main_window.clear_connections() or True,
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="canvas.start_connection",
        name_i18n="k_canvas_start_connection",
        category=ActionCategory.CANVAS,
        description_i18n="k_canvas_start_connection",
        execute_fn=lambda ctx: main_window.get_canvas()._start_connection_by_name(ctx.node_name) if ctx.node_name and hasattr(main_window, 'get_canvas') else False,
        requires_node=True,
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="canvas.clear_selection",
        name_i18n="k_select_clear",
        category=ActionCategory.CANVAS,
        description_i18n="k_select_clear",
        execute_fn=lambda ctx: main_window.get_canvas().clear_box_selection() if hasattr(main_window, 'get_canvas') else False,
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="canvas.reset_view",
        name_i18n="k_canvas_reset_view",
        category=ActionCategory.CANVAS,
        description_i18n="k_canvas_reset_view",
        execute_fn=lambda ctx: main_window.get_canvas().reset_view() if hasattr(main_window, 'get_canvas') else False,
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="canvas.clear_listen_config",
        name_i18n="k_canvas_clear_config",
        category=ActionCategory.CANVAS,
        description_i18n="k_canvas_clear_config",
        execute_fn=lambda ctx: main_window.get_canvas().batch_clear_listen_config() if hasattr(main_window, 'get_canvas') else False,
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="canvas.delete_edge",
        name_i18n="k_canvas_delete_edge",
        category=ActionCategory.CANVAS,
        description_i18n="k_canvas_delete_edge",
        execute_fn=lambda ctx: False,
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="canvas.change_edge_color",
        name_i18n="k_canvas_change_edge_color",
        category=ActionCategory.CANVAS,
        description_i18n="k_canvas_change_edge_color",
        execute_fn=lambda ctx: False,
    ))

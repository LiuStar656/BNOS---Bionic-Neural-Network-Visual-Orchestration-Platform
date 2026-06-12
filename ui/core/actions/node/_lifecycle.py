"""节点生命周期操作 — start / stop / config / refresh / mount / export"""
from ..action_definition import ActionDefinition, ActionCategory, ActionContext
from ..action_registry import ActionRegistry


def register(main_window):
    """注册节点启动/停止/配置/刷新/挂载/导出 action"""

    def execute_node_start(ctx: ActionContext) -> bool:
        if ctx.node_name:
            if hasattr(main_window, 'start_selected_node_by_name'):
                main_window.start_selected_node_by_name(ctx.node_name)
            else:
                main_window.start_selected_node()
            return True
        elif ctx.node_list:
            for name in ctx.node_list:
                if hasattr(main_window, 'start_selected_node_by_name'):
                    main_window.start_selected_node_by_name(name)
            return True
        main_window.start_selected_node()
        return True

    def is_node_start_enabled(ctx: ActionContext) -> bool:
        if ctx.node_name and hasattr(main_window, 'nodes_data'):
            node_info = main_window.nodes_data.get(ctx.node_name, {})
            return node_info.get('status') == 'stopped'
        return True

    ActionRegistry.register(ActionDefinition(
        id="node.start", name_i18n="k_node_start", category=ActionCategory.NODE,
        shortcut_id="start_node", description_i18n="_k_start_node_tip",
        execute_fn=execute_node_start, is_enabled_fn=is_node_start_enabled, requires_node=True))

    def execute_node_stop(ctx: ActionContext) -> bool:
        if ctx.node_name:
            if hasattr(main_window, 'stop_selected_node_by_name'):
                main_window.stop_selected_node_by_name(ctx.node_name)
            else:
                main_window.stop_selected_node()
            return True
        main_window.stop_selected_node()
        return True

    def is_node_stop_enabled(ctx: ActionContext) -> bool:
        if ctx.node_name and hasattr(main_window, 'nodes_data'):
            node_info = main_window.nodes_data.get(ctx.node_name, {})
            return node_info.get('status') in ('running', 'idle')
        return True

    ActionRegistry.register(ActionDefinition(
        id="node.stop", name_i18n="k_node_stop", category=ActionCategory.NODE,
        shortcut_id="stop_node", description_i18n="_k_stop_node_tip",
        execute_fn=execute_node_stop, is_enabled_fn=is_node_stop_enabled, requires_node=True))

    def execute_node_config(ctx: ActionContext) -> bool:
        if ctx.node_name:
            canvas = None
            if ctx.extra and 'canvas' in ctx.extra:
                canvas = ctx.extra['canvas']
            if canvas is None and hasattr(main_window, 'canvas'):
                canvas = main_window.canvas
            if canvas is None and hasattr(main_window, 'get_canvas'):
                canvas = main_window.get_canvas()
            if canvas and hasattr(canvas, 'open_node_config'):
                canvas.open_node_config(ctx.node_name)
                return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.config", name_i18n="k_node_config", category=ActionCategory.NODE,
        description_i18n="k_node_config",
        execute_fn=execute_node_config, requires_node=True))

    ActionRegistry.register(ActionDefinition(
        id="node.refresh", name_i18n="k_node_refresh", category=ActionCategory.NODE,
        shortcut_id="refresh_nodes", description_i18n="k_node_refresh_list",
        execute_fn=lambda ctx: (main_window.refresh_nodes(), True)[1]))

    ActionRegistry.register(ActionDefinition(
        id="node.mount", name_i18n="k_node_mount", category=ActionCategory.NODE,
        shortcut_id="mount_external", description_i18n="k_node_mount_help",
        execute_fn=lambda ctx: (main_window.mount_external_node(), True)[1]))

    ActionRegistry.register(ActionDefinition(
        id="node.export", name_i18n="k_export_node", category=ActionCategory.NODE,
        description_i18n="k_export_node_desc",
        execute_fn=lambda ctx: main_window.export_node(ctx.node_name) if ctx.node_name else main_window.export_node() or True,
        requires_node=True))

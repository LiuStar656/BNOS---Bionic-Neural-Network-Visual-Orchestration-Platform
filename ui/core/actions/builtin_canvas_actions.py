"""
内置画布操作功能定义
所有画布右键菜单操作在此统一注册，通过 extra={'canvas': self} 桥接
"""
from .action_definition import ActionDefinition, ActionCategory, ActionContext
from .action_registry import ActionRegistry


def register_canvas_actions(main_window):
    """注册画布相关功能"""

    def _get_canvas(ctx):
        """统一 canvas 获取：extra → main_window.canvas → main_window.get_canvas()"""
        canvas = (ctx.extra or {}).get('canvas') if ctx.extra else None
        if canvas is None and hasattr(main_window, 'canvas'):
            canvas = main_window.canvas
        if canvas is None and hasattr(main_window, 'get_canvas'):
            canvas = main_window.get_canvas()
        return canvas

    # ======================== 基础画布操作 ========================

    ActionRegistry.register(ActionDefinition(
        id="canvas.clear_connections",
        name_i18n="k_canvas_clear_connections",
        category=ActionCategory.CANVAS,
        shortcut_id="clear_connections",
        description_i18n="k_canvas_clear_connections_desc",
        execute_fn=lambda ctx: main_window.clear_connections() or True,
    ))

    def execute_clear_selection(ctx):
        canvas = _get_canvas(ctx)
        if canvas and hasattr(canvas, 'clear_box_selection'):
            canvas.clear_box_selection()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.clear_selection",
        name_i18n="k_select_clear",
        category=ActionCategory.CANVAS,
        description_i18n="k_select_clear",
        execute_fn=execute_clear_selection,
    ))

    def execute_reset_view(ctx):
        canvas = _get_canvas(ctx)
        if canvas and hasattr(canvas, 'reset_view'):
            canvas.reset_view()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.reset_view",
        name_i18n="k_canvas_reset_view",
        category=ActionCategory.CANVAS,
        description_i18n="k_canvas_reset_view",
        execute_fn=execute_reset_view,
    ))

    def execute_clear_listen_config(ctx):
        canvas = _get_canvas(ctx)
        if canvas and hasattr(canvas, 'batch_clear_listen_config'):
            canvas.batch_clear_listen_config()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.clear_listen_config",
        name_i18n="k_canvas_clear_config",
        category=ActionCategory.CANVAS,
        description_i18n="k_canvas_clear_config",
        execute_fn=execute_clear_listen_config,
    ))

    # ======================== 连线操作 ========================

    def execute_canvas_start_connection(ctx: ActionContext) -> bool:
        canvas = (ctx.extra or {}).get('canvas') if ctx.extra else None
        if canvas and ctx.node_name:
            canvas._start_connection_by_name(ctx.node_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.start_connection",
        name_i18n="k_canvas_start_connection",
        category=ActionCategory.CANVAS,
        description_i18n="k_canvas_start_connection",
        execute_fn=execute_canvas_start_connection,
        requires_node=True,
    ))

    def execute_canvas_delete_edge(ctx: ActionContext) -> bool:
        canvas = (ctx.extra or {}).get('canvas') if ctx.extra else None
        edge = (ctx.extra or {}).get('edge') if ctx.extra else None
        if canvas and edge:
            canvas.remove_edge(edge)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.delete_edge",
        name_i18n="k_canvas_delete_edge",
        category=ActionCategory.CANVAS,
        description_i18n="k_canvas_delete_edge",
        execute_fn=execute_canvas_delete_edge,
    ))

    def execute_canvas_change_edge_color(ctx: ActionContext) -> bool:
        edge = (ctx.extra or {}).get('edge') if ctx.extra else None
        if edge:
            edge.change_edge_color()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.change_edge_color",
        name_i18n="k_canvas_change_edge_color",
        category=ActionCategory.CANVAS,
        description_i18n="k_canvas_change_edge_color",
        execute_fn=execute_canvas_change_edge_color,
    ))

    # ======================== 节点画布操作（通过 extra.canvas 桥接）========================

    def execute_canvas_remove_node(ctx: ActionContext) -> bool:
        canvas = (ctx.extra or {}).get('canvas') if ctx.extra else None
        if canvas and ctx.node_name:
            canvas.remove_node_with_cleanup(ctx.node_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.remove_node",
        name_i18n="k_canvas_remove_from",
        category=ActionCategory.CANVAS,
        execute_fn=execute_canvas_remove_node,
        requires_node=True,
    ))

    def execute_canvas_batch_remove(ctx: ActionContext) -> bool:
        canvas = (ctx.extra or {}).get('canvas') if ctx.extra else None
        if canvas:
            canvas.batch_remove_nodes_from_canvas()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.batch_remove",
        name_i18n="_k_batch_remove_selected",
        category=ActionCategory.CANVAS,
        execute_fn=execute_canvas_batch_remove,
    ))

    def execute_canvas_expand_node(ctx: ActionContext) -> bool:
        canvas = (ctx.extra or {}).get('canvas') if ctx.extra else None
        if canvas and ctx.node_name:
            canvas.on_node_expand_requested(ctx.node_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.expand_node",
        name_i18n="k_node_expand",
        category=ActionCategory.CANVAS,
        execute_fn=execute_canvas_expand_node,
        requires_node=True,
    ))

    # ======================== 工具栏 / 监控 ========================

    def execute_canvas_toggle_draw_toolbar(ctx: ActionContext) -> bool:
        canvas = (ctx.extra or {}).get('canvas') if ctx.extra else None
        if canvas:
            canvas._toggle_draw_toolbar()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.toggle_draw_toolbar",
        name_i18n="k_canvas_show_draw_toolbar",
        category=ActionCategory.CANVAS,
        execute_fn=execute_canvas_toggle_draw_toolbar,
    ))

    def execute_canvas_monitor(ctx: ActionContext) -> bool:
        canvas = (ctx.extra or {}).get('canvas') if ctx.extra else None
        if canvas and canvas.parent_window:
            canvas.parent_window.show_node_monitor_dock()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.monitor",
        name_i18n="k_canvas_monitor",
        category=ActionCategory.CANVAS,
        execute_fn=execute_canvas_monitor,
    ))

    # ======================== 新建节点 ========================

    def _make_new_node_fn(lang):
        def execute(ctx: ActionContext) -> bool:
            canvas = (ctx.extra or {}).get('canvas') if ctx.extra else None
            if canvas and canvas.parent_window:
                canvas.parent_window.create_new_node_with_language(lang)
                return True
            return False
        return execute

    _lang_i18n_map = [
        ("k_lang_python", "Python"),
        ("k_lang_rust", "Rust"),
        ("k_lang_nodejs", "Node.js (开发中)"),
        ("k_lang_go", "Go (开发中)"),
        ("k_lang_java", "Java (开发中)"),
        ("k_lang_cpp", "C++ (开发中)"),
        ("k_lang_shell", "Shell (开发中)"),
    ]
    for i18n_key, lang_name in _lang_i18n_map:
        ActionRegistry.register(ActionDefinition(
            id=f"canvas.new_node.{lang_name}",
            name_i18n=i18n_key,
            category=ActionCategory.CANVAS,
            execute_fn=_make_new_node_fn(lang_name),
        ))

    # ======================== 画布颜色设置 ========================

    def execute_canvas_bg_color(ctx: ActionContext) -> bool:
        canvas = (ctx.extra or {}).get('canvas') if ctx.extra else None
        if canvas:
            canvas.change_canvas_background_color()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.bg_color",
        name_i18n="k_canvas_bg_color",
        category=ActionCategory.CANVAS,
        execute_fn=execute_canvas_bg_color,
    ))

    def execute_canvas_grid_color(ctx: ActionContext) -> bool:
        canvas = (ctx.extra or {}).get('canvas') if ctx.extra else None
        if canvas:
            canvas.change_grid_color()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.grid_color",
        name_i18n="k_canvas_grid_color",
        category=ActionCategory.CANVAS,
        execute_fn=execute_canvas_grid_color,
    ))

    def execute_canvas_default_edge_color(ctx: ActionContext) -> bool:
        canvas = (ctx.extra or {}).get('canvas') if ctx.extra else None
        if canvas:
            canvas.change_edge_color()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.default_edge_color",
        name_i18n="k_canvas_edge_color",
        category=ActionCategory.CANVAS,
        execute_fn=execute_canvas_default_edge_color,
    ))

    # ======================== 全局快捷键操作 ========================

    def execute_canvas_delete_selected(ctx: ActionContext) -> bool:
        canvas = _get_canvas(ctx)
        if canvas and hasattr(canvas.parent_window, '_on_ctrl_d'):
            canvas.parent_window._on_ctrl_d()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="canvas.delete_selected",
        name_i18n="_k_delete_selected",
        category=ActionCategory.CANVAS,
        shortcut_id="delete_selected",
        description_i18n="_k_delete_selected",
        execute_fn=execute_canvas_delete_selected,
    ))

    def execute_workspace_open_vscode(ctx: ActionContext) -> bool:
        from ui.core.ide_scanner import ide_scanner
        workspace_path = (ctx.extra or {}).get('workspace_path', '')
        if workspace_path:
            return ide_scanner.open_in_vscode(workspace_path)
        return False

    ActionRegistry.register(ActionDefinition(
        id="workspace.open_vscode",
        name_i18n="k_open_vscode",
        category=ActionCategory.CANVAS,
        execute_fn=execute_workspace_open_vscode,
    ))

    def execute_workspace_open_trae(ctx: ActionContext) -> bool:
        from ui.core.ide_scanner import ide_scanner
        workspace_path = (ctx.extra or {}).get('workspace_path', '')
        if workspace_path:
            return ide_scanner.open_in_trae(workspace_path)
        return False

    ActionRegistry.register(ActionDefinition(
        id="workspace.open_trae_ide",
        name_i18n="_k_open_trae",
        category=ActionCategory.CANVAS,
        execute_fn=execute_workspace_open_trae,
    ))

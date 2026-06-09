"""
内置节点操作功能定义
"""
from .action_definition import ActionDefinition, ActionCategory, ActionContext
from .action_registry import ActionRegistry


def register_node_actions(main_window):
    """注册节点相关功能"""
    
    def execute_node_start(ctx: ActionContext) -> bool:
        if ctx.node_name:
            if hasattr(main_window, 'start_selected_node_by_name'):
                main_window.start_selected_node_by_name(ctx.node_name)
            else:
                # 兼容旧接口
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
        id="node.start",
        name_i18n="k_node_start",
        category=ActionCategory.NODE,
        shortcut_id="start_node",
        description_i18n="_k_start_node_tip",
        execute_fn=execute_node_start,
        is_enabled_fn=is_node_start_enabled,
        requires_node=True,
    ))
    
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
        id="node.stop",
        name_i18n="k_node_stop",
        category=ActionCategory.NODE,
        shortcut_id="stop_node",
        description_i18n="_k_stop_node_tip",
        execute_fn=execute_node_stop,
        is_enabled_fn=is_node_stop_enabled,
        requires_node=True,
    ))
    
    def execute_node_config(ctx: ActionContext) -> bool:
        if ctx.node_name:
            # 优先从 context 中取 canvas 引用（通过 _make_ctx 注入）
            canvas = None
            if ctx.extra and 'canvas' in ctx.extra:
                canvas = ctx.extra['canvas']
            # 否则从 main_window 获取（canvas 是直接属性）
            if canvas is None and hasattr(main_window, 'canvas'):
                canvas = main_window.canvas
            # 最后兜底
            if canvas is None and hasattr(main_window, 'get_canvas'):
                canvas = main_window.get_canvas()
            if canvas and hasattr(canvas, 'open_node_config'):
                canvas.open_node_config(ctx.node_name)
                return True
        return False
    
    ActionRegistry.register(ActionDefinition(
        id="node.config",
        name_i18n="k_node_config",
        category=ActionCategory.NODE,
        description_i18n="k_node_config",
        execute_fn=execute_node_config,
        requires_node=True,
    ))
    
    def execute_node_refresh(ctx: ActionContext) -> bool:
        main_window.refresh_nodes()
        return True
    
    ActionRegistry.register(ActionDefinition(
        id="node.refresh",
        name_i18n="k_node_refresh",
        category=ActionCategory.NODE,
        shortcut_id="refresh_nodes",
        description_i18n="k_node_refresh_list",
        execute_fn=execute_node_refresh,
    ))
    
    def execute_node_mount(ctx: ActionContext) -> bool:
        main_window.mount_external_node()
        return True
    
    ActionRegistry.register(ActionDefinition(
        id="node.mount",
        name_i18n="k_node_mount",
        category=ActionCategory.NODE,
        shortcut_id="mount_external",
        description_i18n="k_node_mount_help",
        execute_fn=execute_node_mount,
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="node.export",
        name_i18n="k_export_node",
        category=ActionCategory.NODE,
        description_i18n="k_export_node_desc",
        execute_fn=lambda ctx: main_window.export_node(ctx.node_name) if ctx.node_name else main_window.export_node() or True,
        requires_node=True,
    ))

    # ======================== 节点右键菜单操作（通过 panel extra 桥接）========================

    def execute_node_add_to_canvas(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.node_name:
            panel.add_node_to_canvas(ctx.node_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.add_to_canvas",
        name_i18n="k_canvas_add_to",
        category=ActionCategory.NODE,
        execute_fn=execute_node_add_to_canvas,
        requires_node=True,
    ))

    def execute_node_open_folder(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.node_name:
            panel.open_node_folder(ctx.node_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.open_folder",
        name_i18n="k_open_dir",
        category=ActionCategory.NODE,
        execute_fn=execute_node_open_folder,
        requires_node=True,
    ))

    def execute_node_view_log(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.node_name:
            panel.view_node_log(ctx.node_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.view_log",
        name_i18n="k_view_log",
        category=ActionCategory.NODE,
        execute_fn=execute_node_view_log,
        requires_node=True,
    ))

    def execute_node_edit_config(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.node_name:
            panel.edit_node_config(ctx.node_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.edit_config",
        name_i18n="k_edit_config",
        category=ActionCategory.NODE,
        execute_fn=execute_node_edit_config,
        requires_node=True,
    ))

    def execute_node_rename(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.node_name:
            panel.rename_node(ctx.node_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.rename",
        name_i18n="k_node_rename",
        category=ActionCategory.NODE,
        execute_fn=execute_node_rename,
        requires_node=True,
    ))

    def execute_node_delete(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.node_name:
            panel.delete_node(ctx.node_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.delete",
        name_i18n="k_node_delete",
        category=ActionCategory.NODE,
        execute_fn=execute_node_delete,
        requires_node=True,
    ))

    def execute_node_unmount(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.node_name:
            panel._unmount_node(ctx.node_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.unmount",
        name_i18n="k_node_unmount",
        category=ActionCategory.NODE,
        execute_fn=execute_node_unmount,
        requires_node=True,
    ))

    # ======================== 批量节点操作 ========================

    def execute_node_batch_add_to_canvas(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel:
            panel.batch_add_nodes_to_canvas()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.batch_add_to_canvas",
        name_i18n="_k_add_n_to_canvas",
        category=ActionCategory.NODE,
        execute_fn=execute_node_batch_add_to_canvas,
    ))

    def execute_node_batch_open_folders(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel:
            panel.batch_open_node_folders()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.batch_open_folders",
        name_i18n="_k_open_n_dirs",
        category=ActionCategory.NODE,
        execute_fn=execute_node_batch_open_folders,
    ))

    def execute_node_batch_view_logs(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel:
            panel.batch_view_node_logs()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.batch_view_logs",
        name_i18n="_k_view_n_logs",
        category=ActionCategory.NODE,
        execute_fn=execute_node_batch_view_logs,
    ))

    def execute_node_batch_edit_configs(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel:
            panel.batch_edit_node_configs()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.batch_edit_configs",
        name_i18n="_k_edit_n_configs",
        category=ActionCategory.NODE,
        execute_fn=execute_node_batch_edit_configs,
    ))

    def execute_node_batch_delete(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel:
            panel.batch_delete_nodes()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.batch_delete",
        name_i18n="_k_delete_n_nodes",
        category=ActionCategory.NODE,
        execute_fn=execute_node_batch_delete,
    ))

    # ======================== 选择操作 ========================

    def execute_select_all(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel:
            panel.select_all_nodes()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.select_all",
        name_i18n="k_select_all",
        category=ActionCategory.NODE,
        execute_fn=execute_select_all,
    ))

    def execute_deselect_all(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel:
            panel.deselect_all_nodes()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.deselect_all",
        name_i18n="k_select_cancel",
        category=ActionCategory.NODE,
        execute_fn=execute_deselect_all,
    ))

    # ======================== 组操作 ========================

    def execute_group_create(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel:
            panel.create_node_group()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="group.create",
        name_i18n="k_group_create",
        category=ActionCategory.NODE,
        execute_fn=execute_group_create,
    ))

    def execute_group_move_to(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.node_name and ctx.group_name:
            panel.move_node_to_group(ctx.node_name, ctx.group_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="group.move_to",
        name_i18n="k_group_move",
        category=ActionCategory.NODE,
        execute_fn=execute_group_move_to,
    ))

    def execute_group_batch_move_to(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.group_name:
            panel.batch_move_nodes_to_group(ctx.group_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="group.batch_move_to",
        name_i18n="k_group_move",
        category=ActionCategory.NODE,
        execute_fn=execute_group_batch_move_to,
    ))

    def execute_group_remove_from(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.node_name:
            panel.remove_node_from_group(ctx.node_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="group.remove_from",
        name_i18n="_k_group_remove_from",
        category=ActionCategory.NODE,
        execute_fn=execute_group_remove_from,
    ))

    def execute_group_batch_remove_from(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.group_name:
            panel.batch_remove_nodes_from_group(ctx.group_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="group.batch_remove_from",
        name_i18n="_k_group_remove_from",
        category=ActionCategory.NODE,
        execute_fn=execute_group_batch_remove_from,
    ))

    def execute_group_rename(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.group_name:
            panel.rename_group(ctx.group_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="group.rename",
        name_i18n="k_group_rename",
        category=ActionCategory.NODE,
        execute_fn=execute_group_rename,
    ))

    def execute_group_delete(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.group_name:
            panel.delete_group(ctx.group_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="group.delete",
        name_i18n="k_group_delete",
        category=ActionCategory.NODE,
        execute_fn=execute_group_delete,
    ))

    def execute_group_start(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.group_name:
            panel.start_group_nodes(ctx.group_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="group.start",
        name_i18n="_k_start_group_nodes",
        category=ActionCategory.NODE,
        execute_fn=execute_group_start,
    ))

    def execute_group_stop(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.group_name:
            panel.stop_group_nodes(ctx.group_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="group.stop",
        name_i18n="_k_stop_group_nodes",
        category=ActionCategory.NODE,
        execute_fn=execute_group_stop,
    ))

    def execute_group_toggle_expand(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel and ctx.group_name:
            panel.toggle_group_expansion(ctx.group_name)
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="group.toggle_expand",
        name_i18n="k_group_expand_collapse",
        category=ActionCategory.NODE,
        execute_fn=execute_group_toggle_expand,
    ))

    # ======================== 未分组节点操作 ========================

    def execute_ungrouped_start(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel:
            panel.start_ungrouped_nodes()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="ungrouped.start",
        name_i18n="_k_start_ungrouped",
        category=ActionCategory.NODE,
        execute_fn=execute_ungrouped_start,
    ))

    def execute_ungrouped_stop(ctx: ActionContext) -> bool:
        panel = (ctx.extra or {}).get('panel')
        if panel:
            panel.stop_ungrouped_nodes()
            return True
        return False

    ActionRegistry.register(ActionDefinition(
        id="ungrouped.stop",
        name_i18n="_k_stop_ungrouped",
        category=ActionCategory.NODE,
        execute_fn=execute_ungrouped_stop,
    ))

    # ======================== IDE 操作（通过 Action 系统统一管理） ========================

    def execute_node_open_vscode(ctx: ActionContext) -> bool:
        from ui.core.ide_scanner import ide_scanner
        node_name = (ctx.extra or {}).get('node_name', ctx.node_name or '')
        node_path = (ctx.extra or {}).get('node_path', '')
        if node_name and node_path:
            return ide_scanner.open_vscode_workspace(node_name, node_path)
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.open_vscode",
        name_i18n="k_open_vscode",
        category=ActionCategory.NODE,
        execute_fn=execute_node_open_vscode,
        requires_node=True,
    ))

    def execute_node_open_trae(ctx: ActionContext) -> bool:
        from ui.core.ide_scanner import ide_scanner
        node_path = (ctx.extra or {}).get('node_path', '')
        if node_path:
            return ide_scanner.open_in_trae(node_path)
        return False

    ActionRegistry.register(ActionDefinition(
        id="node.open_trae_ide",
        name_i18n="_k_open_trae",
        category=ActionCategory.NODE,
        execute_fn=execute_node_open_trae,
        requires_node=True,
    ))

# register_node_actions 结束

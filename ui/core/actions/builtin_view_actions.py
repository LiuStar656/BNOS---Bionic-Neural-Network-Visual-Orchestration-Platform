"""
内置视图操作功能定义
"""
from .action_definition import ActionDefinition, ActionCategory, ActionContext
from .action_registry import ActionRegistry
from ui.core.i18n import t


def register_view_actions(main_window):
    """注册视图相关功能"""
    
    def _toggle_node_list_dock(ctx):
        """切换节点列表Dock - 使用正确的面板系统"""
        panel = getattr(main_window, 'node_list_panel', None)
        if panel is not None and panel.isVisible():
            # 面板已显示 → 关闭
            main_window.toggle_node_list_panel(False)
        else:
            # 面板未显示 → 打开
            main_window.toggle_node_list_panel(True)
        return True

    ActionRegistry.register(ActionDefinition(
        id="view.toggle_node_list",
        name_i18n="k_node_list_dock",
        category=ActionCategory.VIEW,
        description_i18n="k_menu_toggle_nodes",
        execute_fn=_toggle_node_list_dock,
        is_checked_fn=lambda ctx: (
            getattr(main_window, 'node_list_panel', None) is not None
            and main_window.node_list_panel.isVisible()
        ) if getattr(main_window, 'node_list_panel', None) else main_window.app_config.get('panel_visibility', {}).get('node_list_dock', False),
    ))
    
    def _toggle_node_monitor_dock(ctx):
        """切换节点监测Dock"""
        panel = getattr(main_window, 'node_monitor_dock', None)
        if panel is not None and panel.isVisible():
            dock_mgr = getattr(main_window, '_dock_manager', None)
            if dock_mgr and hasattr(dock_mgr, 'get_dock_by_title'):
                d = dock_mgr.get_dock_by_title(t("k_node_monitor_dock"))
                if d: d.close()
        else:
            main_window.show_node_monitor_dock()
        return True

    def _toggle_resource_monitor_dock(ctx):
        """切换资源监测Dock"""
        panel = getattr(main_window, 'resource_monitor', None)
        if panel is not None and panel.isVisible():
            dock_mgr = getattr(main_window, '_dock_manager', None)
            if dock_mgr and hasattr(dock_mgr, 'get_dock_by_title'):
                d = dock_mgr.get_dock_by_title(t("k_resource_monitor_dock"))
                if d: d.close()
        else:
            main_window.show_resource_monitor_dock()
        return True

    ActionRegistry.register(ActionDefinition(
        id="view.toggle_node_monitor",
        name_i18n="k_node_monitor_dock",
        category=ActionCategory.VIEW,
        description_i18n="k_node_monitor_dock_desc",
        execute_fn=_toggle_node_monitor_dock,
        is_checked_fn=lambda ctx: (
            getattr(main_window, 'node_monitor_dock', None) is not None
            and main_window.node_monitor_dock.isVisible()
        ) if getattr(main_window, 'node_monitor_dock', None) else main_window.app_config.get('panel_visibility', {}).get('node_monitor_dock', False),
    ))

    ActionRegistry.register(ActionDefinition(
        id="view.toggle_resource_monitor",
        name_i18n="k_resource_monitor_dock",
        category=ActionCategory.VIEW,
        description_i18n="k_resource_monitor_desc",
        execute_fn=_toggle_resource_monitor_dock,
        is_checked_fn=lambda ctx: (
            getattr(main_window, 'resource_monitor', None) is not None
            and main_window.resource_monitor.isVisible()
        ) if getattr(main_window, 'resource_monitor', None) else main_window.app_config.get('panel_visibility', {}).get('resource_monitor_dock', False),
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="view.color_settings",
        name_i18n="k_color_settings",
        category=ActionCategory.VIEW,
        description_i18n="k_color_settings_desc",
        execute_fn=lambda ctx: (main_window.open_color_settings(), True)[1],
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="view.settings",
        name_i18n="_k_settings_title",
        category=ActionCategory.VIEW,
        shortcut_id="settings",
        description_i18n="_k_settings_title",
        execute_fn=lambda ctx: (main_window.open_settings(), True)[1],
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="view.toggle_terminal",
        name_i18n="k_view_toggle_terminal",
        category=ActionCategory.VIEW,
        description_i18n="k_menu_toggle_terminal",
        execute_fn=lambda ctx: (main_window.toggle_terminal(), True)[1],
        is_checked_fn=lambda ctx: main_window.app_config.get('panel_visibility', {}).get(
            'terminal_dock', False
        ),
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="view.about",
        name_i18n="k_menu_about",
        category=ActionCategory.VIEW,
        description_i18n="k_menu_about_desc",
        execute_fn=lambda ctx: (main_window.show_about(), True)[1],
    ))

    ActionRegistry.register(ActionDefinition(
        id="view.changelog",
        name_i18n="k_menu_changelog",
        category=ActionCategory.VIEW,
        description_i18n="k_menu_changelog_desc",
        execute_fn=lambda ctx: (main_window.show_changelog(), True)[1],
    ))

    ActionRegistry.register(ActionDefinition(
        id="view.history_panel",
        name_i18n="k_view_history_panel",
        category=ActionCategory.VIEW,
        description_i18n="k_view_history_panel",
        execute_fn=lambda ctx: (main_window.show_history_panel(), True)[1],
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="view.performance_panel",
        name_i18n="k_performance_panel",
        category=ActionCategory.VIEW,
        description_i18n="k_performance",
        execute_fn=lambda ctx: (main_window.show_performance_panel(), True)[1],
        is_checked_fn=lambda ctx: main_window.app_config.get('panel_visibility', {}).get('performance_dock', False),
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="view.template_selector",
        name_i18n="k_select_template",
        category=ActionCategory.VIEW,
        description_i18n="k_preset_library",
        execute_fn=lambda ctx: (main_window.show_template_selector(), True)[1],
        is_checked_fn=lambda ctx: main_window.app_config.get('panel_visibility', {}).get('preset_library_dock', False),
    ))

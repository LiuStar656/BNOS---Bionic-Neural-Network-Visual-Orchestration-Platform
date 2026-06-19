"""
内置视图操作功能定义
"""
from .action_definition import ActionDefinition, ActionCategory, ActionContext
from .action_registry import ActionRegistry


def register_view_actions(main_window):
    """注册视图相关功能"""
    
    ActionRegistry.register(ActionDefinition(
        id="view.toggle_node_list",
        name_i18n="k_node_list_dock",
        category=ActionCategory.VIEW,
        description_i18n="k_menu_toggle_nodes",
        execute_fn=lambda ctx: (main_window.panel_manager.toggle_panel("node_list"), True)[1],
        is_checked_fn=lambda ctx: main_window.app_config.get('panel_visibility', {}).get(
            'node_list_dock', main_window.app_config.get('panel_visibility', {}).get('node_list', False)
        ),
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="view.toggle_node_monitor",
        name_i18n="k_node_monitor_dock",
        category=ActionCategory.VIEW,
        description_i18n="k_node_monitor_dock_desc",
        execute_fn=lambda ctx: (main_window.show_node_monitor_dock(), True)[1],
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="view.toggle_resource_monitor",
        name_i18n="k_resource_monitor_dock",
        category=ActionCategory.VIEW,
        description_i18n="k_resource_monitor_desc",
        execute_fn=lambda ctx: (main_window.show_resource_monitor_dock(), True)[1],
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="view.node_monitor",
        name_i18n="k_node_monitor",
        category=ActionCategory.VIEW,
        shortcut_id="node_monitor",
        description_i18n="k_menu_monitor",
        execute_fn=lambda ctx: (main_window.show_node_monitor(), True)[1],
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="view.resource_monitor",
        name_i18n="k_resource_monitor",
        category=ActionCategory.VIEW,
        shortcut_id="resource_monitor",
        description_i18n="k_resource_monitor_desc",
        execute_fn=lambda ctx: (main_window.show_resource_monitor(), True)[1],
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="view.node_list_floating",
        name_i18n="k_node_list",
        category=ActionCategory.VIEW,
        description_i18n="k_menu_toggle_nodes",
        execute_fn=lambda ctx: (main_window.show_node_list_floating(), True)[1],
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
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="view.debug_panel",
        name_i18n="k_debug_panel",
        category=ActionCategory.VIEW,
        description_i18n="k_debug",
        execute_fn=lambda ctx: (main_window.show_debug_panel(), True)[1],
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="view.template_selector",
        name_i18n="k_select_template",
        category=ActionCategory.VIEW,
        description_i18n="k_preset_library",
        execute_fn=lambda ctx: (main_window.show_template_selector(), True)[1],
    ))

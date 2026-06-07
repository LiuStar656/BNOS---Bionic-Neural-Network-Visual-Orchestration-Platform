"""
内置项目操作功能定义
"""
from .action_definition import ActionDefinition, ActionCategory, ActionContext
from .action_registry import ActionRegistry
from ui.core.i18n import t


def register_project_actions(main_window):
    """注册项目相关功能"""
    
    ActionRegistry.register(ActionDefinition(
        id="project.new",
        name_i18n="k_project_new",
        category=ActionCategory.PROJECT,
        shortcut_id="new_project",
        description_i18n="k_node_create_desc",
        execute_fn=lambda ctx: main_window.new_project() or True,
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="project.open",
        name_i18n="k_project_open",
        category=ActionCategory.PROJECT,
        shortcut_id="open_project",
        description_i18n="k_menu_open_project_desc",
        execute_fn=lambda ctx: main_window.open_project() or True,
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="project.import_node",
        name_i18n="k_import_node",
        category=ActionCategory.PROJECT,
        description_i18n="k_import_node_desc",
        execute_fn=lambda ctx: main_window.import_node() or True,
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="project.export_node",
        name_i18n="k_export_node",
        category=ActionCategory.PROJECT,
        description_i18n="k_export_node_desc",
        execute_fn=lambda ctx: main_window.export_node(ctx.node_name) if ctx.node_name else main_window.export_node() or True,
        requires_node=False,
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="project.export_project",
        name_i18n="k_export_project",
        category=ActionCategory.PROJECT,
        description_i18n="k_export_project_desc",
        execute_fn=lambda ctx: main_window.export_project() or True,
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="project.restart",
        name_i18n="k_menu_restart",
        category=ActionCategory.PROJECT,
        shortcut_id="restart",
        description_i18n="k_menu_restart_desc",
        execute_fn=lambda ctx: main_window._restart_application() or True,
    ))
    
    ActionRegistry.register(ActionDefinition(
        id="project.exit",
        name_i18n="k_menu_exit",
        category=ActionCategory.PROJECT,
        shortcut_id="exit_app",
        description_i18n="k_menu_exit_desc",
        execute_fn=lambda ctx: (main_window.close(), True)[1],
    ))

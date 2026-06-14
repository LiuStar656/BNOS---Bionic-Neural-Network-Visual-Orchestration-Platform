"""
Action 创建工厂模块 — 从统一注册表创建 QAction
"""
from PySide6.QtWidgets import QMenu, QMenuBar
from PySide6.QtGui import QAction
from typing import Optional
from .action_registry import ActionRegistry
from .action_definition import ActionDefinition, ActionContext
from ui.core.i18n import t


class ActionFactory:
    """QAction 创建工厂"""
    
    @staticmethod
    def create_action(
        parent,
        action_id: str,
        context: Optional[ActionContext] = None,
        menu: Optional[QMenu] = None
    ) -> Optional[QAction]:
        """创建 QAction（从统一注册表）"""
        
        action_def = ActionRegistry.get(action_id)
        if not action_def:
            return None
        
        action = QAction(t(action_def.name_i18n), parent)
        
        if action_def.shortcut_id and menu is None:
            if hasattr(parent, 'shortcut_mgr'):
                action.setShortcut(parent.shortcut_mgr.get(action_def.shortcut_id))
        
        current_context = context or ActionContext()
        action.setEnabled(ActionRegistry.is_enabled(action_id, current_context))
        
        if action_def.is_checked_fn:
            action.setCheckable(True)
            action.setChecked(action_def.is_checked_fn(current_context))
        
        if action_def.description_i18n:
            action.setStatusTip(t(action_def.description_i18n))
            action.setToolTip(t(action_def.description_i18n))
        
        def on_triggered(checked=False):
            ActionRegistry.execute(action_id, current_context)
        
        action.triggered.connect(on_triggered)
        
        if menu is not None:
            menu.addAction(action)
        
        return action
    
    @staticmethod
    def create_submenu(
        parent,
        menu_title_i18n: str,
        parent_menu: Optional[QMenu] = None,
        menubar: Optional[QMenuBar] = None
    ) -> QMenu:
        """创建子菜单"""
        title = t(menu_title_i18n)
        if menubar:
            return menubar.addMenu(title)
        elif parent_menu:
            return parent_menu.addMenu(title)
        return QMenu(title, parent)
    
    @staticmethod
    def add_separator(menu: QMenu):
        """添加分隔线"""
        menu.addSeparator()
    
    @staticmethod
    def add_disabled_label(menu: QMenu, text_i18n: str):
        """添加禁用的标签项"""
        action = menu.addAction(t(text_i18n))
        action.setEnabled(False)
        return action

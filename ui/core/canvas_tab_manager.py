"""
画布标签管理器 - 管理多画布实例，实现VSCode式多标签页体验
"""
import os
import json
from PyQt6.QtWidgets import (
    QTabWidget, QTabBar, QWidget, QVBoxLayout, QMenu,
    QMessageBox, QInputDialog
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QIcon
from ui.canvas_widget import NodeCanvas
from ui.core.i18n import t
from ui.core.logger import logger


class CanvasTabManager(QTabWidget):
    """画布标签管理器"""
    
    tab_changed = pyqtSignal(int, str)  # index, project_path
    tab_closed = pyqtSignal(int)
    last_tab_closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent_window = parent
        self._tab_contexts = {}  # index -> context dict
        self._fixed_tabs = set()  # 固定的标签索引
        
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI"""
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setDocumentMode(True)
        self.setTabPosition(QTabWidget.TabPosition.North)  # 标签在顶部
        self.tabCloseRequested.connect(self._close_tab)
        self.currentChanged.connect(self._on_tab_changed)
        self.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabBar().customContextMenuRequested.connect(self._show_tab_menu)
        
        # 设置样式
        self.setStyleSheet("""
            QTabWidget::tab-bar {
                alignment: left;
                height: 22px;
            }
            QTabBar::tab {
                background-color: #252526;
                color: #858585;
                padding: 4px 24px 4px 12px;
                margin-right: 1px;
                margin-bottom: 1px;
                font-size: 11px;
                border: none;
                min-width: 100px;
                max-width: 200px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border-top: 1px solid #007acc;
            }
            QTabBar::tab:hover {
                color: #d4d4d4;
            }
            QTabWidget::pane {
                background-color: #1e1e1e;
                border: none;
            }
            QTabBar::close-button {
                width: 16px;
                height: 16px;
                image: url(:/icons/close.png);
                subcontrol-position: right;
                subcontrol-origin: padding;
            }
            QTabBar::close-button:hover {
                image: url(:/icons/close-hover.png);
            }
            QTabBar::tab:selected QTabBar::close-button {
                image: url(:/icons/close-active.png);
            }
        """)
    
    def _show_tab_menu(self, pos):
        """显示标签右键菜单"""
        index = self.tabBar().tabAt(pos)
        if index < 0:
            return
        
        menu = QMenu()
        
        # 关闭当前标签
        close_action = QAction(t("k_close"), self)
        close_action.triggered.connect(lambda: self._close_tab(index))
        menu.addAction(close_action)
        
        # 关闭其他标签
        if self.count() > 1:
            close_others_action = QAction(t("k_close_others"), self)
            close_others_action.triggered.connect(lambda: self._close_other_tabs(index))
            menu.addAction(close_others_action)
            
            # 关闭右侧标签
            close_right_action = QAction(t("k_close_right"), self)
            close_right_action.triggered.connect(lambda: self._close_tabs_to_right(index))
            menu.addAction(close_right_action)
        
        # 固定/取消固定
        if index in self._fixed_tabs:
            unfix_action = QAction(t("k_unpin"), self)
            unfix_action.triggered.connect(lambda: self._toggle_pin(index, False))
            menu.addAction(unfix_action)
        else:
            pin_action = QAction(t("k_pin"), self)
            pin_action.triggered.connect(lambda: self._toggle_pin(index, True))
            menu.addAction(pin_action)
        
        # 重命名
        rename_action = QAction(t("k_rename"), self)
        rename_action.triggered.connect(lambda: self._rename_tab(index))
        menu.addAction(rename_action)
        
        menu.exec(self.tabBar().mapToGlobal(pos))
    
    def _toggle_pin(self, index, pin):
        """切换标签固定状态"""
        if pin:
            self._fixed_tabs.add(index)
            # 缩短固定标签名称
            text = self.tabText(index)
            if len(text) > 10:
                self.setTabText(index, text[:10] + "...")
        else:
            self._fixed_tabs.discard(index)
            # 恢复完整名称
            context = self._tab_contexts.get(index)
            if context:
                self.setTabText(index, context.get('name', f"Canvas {index + 1}"))
    
    def _rename_tab(self, index):
        """重命名标签"""
        current_text = self.tabText(index)
        new_name, ok = QInputDialog.getText(self, t("k_rename_tab"), t("k_enter_new_name"), text=current_text)
        if ok and new_name:
            self.setTabText(index, new_name)
            context = self._tab_contexts.get(index)
            if context:
                context['name'] = new_name
    
    def _close_other_tabs(self, keep_index):
        """关闭除指定标签外的所有标签"""
        indices_to_close = []
        for i in range(self.count()):
            if i != keep_index:
                indices_to_close.append(i)
        
        # 从后往前关闭
        for i in sorted(indices_to_close, reverse=True):
            self._close_tab(i)
    
    def _close_tabs_to_right(self, start_index):
        """关闭指定标签右侧的所有标签"""
        indices_to_close = []
        for i in range(start_index + 1, self.count()):
            if i not in self._fixed_tabs:
                indices_to_close.append(i)
        
        for i in sorted(indices_to_close, reverse=True):
            self._close_tab(i)
    
    def _close_tab(self, index):
        """关闭标签"""
        # 最后一个标签禁止关闭
        if self.count() <= 1:
            return
        
        # 固定标签需要确认
        if index in self._fixed_tabs:
            reply = QMessageBox.question(
                self, t("k_close_pinned"),
                t("k_close_pinned_confirm"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # 保存布局
        self._save_canvas_layout(index)
        
        # 删除上下文并重新编号
        if index in self._tab_contexts:
            del self._tab_contexts[index]
        
        # 重新编号剩余标签的上下文
        new_contexts = {}
        for i in list(self._tab_contexts.keys()):
            if i < index:
                new_contexts[i] = self._tab_contexts[i]
            elif i > index:
                new_contexts[i - 1] = self._tab_contexts[i]
        self._tab_contexts = new_contexts
        
        # 更新固定标签索引
        new_fixed = set()
        for i in self._fixed_tabs:
            if i < index:
                new_fixed.add(i)
            elif i > index:
                new_fixed.add(i - 1)
        self._fixed_tabs = new_fixed
        
        # 移除标签
        self.removeTab(index)
        
        # 如果关闭的是最后一个标签，发出信号
        if self.count() == 0:
            self.last_tab_closed.emit()
    
    def _save_canvas_layout(self, index):
        """保存画布布局"""
        canvas = self.widget(index)
        if canvas and hasattr(canvas, 'save_layout'):
            context = self._tab_contexts.get(index)
            if context and context.get('project_path'):
                layout_path = os.path.join(context['project_path'], 'canvas_layout.json')
                canvas.save_layout(layout_path)
    
    def _on_tab_changed(self, index):
        """标签切换事件"""
        if index >= 0:
            context = self._tab_contexts.get(index, {})
            project_path = context.get('project_path', '')
            self.tab_changed.emit(index, project_path)
    
    def add_new_tab(self, project_path=None, name=None):
        """添加新标签页"""
        # 创建画布实例
        canvas = NodeCanvas(self._parent_window)
        canvas.parent_window = self._parent_window
        
        # 生成标签名称
        if name:
            tab_name = name
        elif project_path:
            tab_name = os.path.basename(project_path)
        else:
            tab_name = f"{t('k_canvas')} {self.count() + 1}"
        
        # 添加标签
        index = self.addTab(canvas, tab_name)
        self.setCurrentIndex(index)
        
        # 存储上下文
        self._tab_contexts[index] = {
            'project_path': project_path,
            'name': tab_name,
            'canvas': canvas
        }
        
        # 如果有项目路径，加载布局
        if project_path:
            layout_path = os.path.join(project_path, 'canvas_layout.json')
            if os.path.exists(layout_path):
                canvas.load_layout(layout_path)
        
        return index, canvas
    
    def get_current_canvas(self):
        """获取当前活动画布"""
        index = self.currentIndex()
        if index >= 0:
            return self.widget(index)
        return None
    
    def get_current_context(self):
        """获取当前标签上下文"""
        index = self.currentIndex()
        if index >= 0:
            return self._tab_contexts.get(index, {})
        return {}
    
    def get_canvas_by_index(self, index):
        """根据索引获取画布"""
        if 0 <= index < self.count():
            return self.widget(index)
        return None
    
    def get_all_contexts(self):
        """获取所有标签上下文"""
        return list(self._tab_contexts.values())
    
    def save_all_layouts(self):
        """保存所有画布布局"""
        for index, context in self._tab_contexts.items():
            self._save_canvas_layout(index)
    
    def save_tab_state(self):
        """保存标签状态到配置"""
        state = []
        for i in range(self.count()):
            context = self._tab_contexts.get(i, {})
            state.append({
                'project_path': context.get('project_path'),
                'name': context.get('name', self.tabText(i)),
                'is_pinned': i in self._fixed_tabs
            })
        return state
    
    def restore_tab_state(self, state):
        """从配置恢复标签状态"""
        # 清空现有标签
        while self.count() > 0:
            self._close_tab(0)
        
        # 恢复标签
        for item in state:
            index, _ = self.add_new_tab(
                project_path=item.get('project_path'),
                name=item.get('name')
            )
            if item.get('is_pinned'):
                self._toggle_pin(index, True)
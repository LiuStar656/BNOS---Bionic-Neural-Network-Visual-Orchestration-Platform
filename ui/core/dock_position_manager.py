from PySide6.QtCore import Qt, QTimer, QRect, QObject, QEvent
from PySide6.QtWidgets import QDockWidget, QMainWindow, QApplication


class DockedState:
    """停靠状态数据类型"""
    
    def __init__(self, area=None, tab_partners=None):
        self.area = area  # Qt.DockWidgetArea - 停靠区域
        self.tab_partners = tab_partners or []  # 同组的tab伙伴


class FloatingGeometry:
    """悬浮状态数据类型"""
    
    def __init__(self, x=0, y=0, width=0, height=0):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
    
    def is_valid(self):
        return self.width > 0 and self.height > 0


class DockPositionManager(QObject):
    """
    Dock位置管理器 - 统一处理Dock的位置记忆和恢复逻辑
    
    解决问题：Qt原生QDockWidget在拖动浮动窗口后会清空内部停靠区域缓存，
    导致再次双击只能自动吸附到区域右下角。
    
    解决方案：
    1. 定义两种位置状态类型：DockedState（停靠状态）和 FloatingGeometry（悬浮状态）
    2. 在拖动开始时（鼠标按下）保存当前停靠状态，避免Qt清空缓存后保存失败
    3. 在双击切换前再次确认保存状态
    4. 使用多次延迟重试确保位置正确恢复
    """
    
    def __init__(self, dock_widget):
        """
        初始化位置管理器
        
        Args:
            dock_widget: QDockWidget或其子类实例
        """
        super().__init__()
        self._dock_widget = dock_widget
        self._original_dock_area = None
        
        self._last_docked_state = DockedState()
        self._last_floating_geometry = FloatingGeometry()
        
        self._connect_signals()
        self._install_mouse_event_filter()
    
    def _connect_signals(self):
        """连接信号"""
        self._dock_widget.topLevelChanged.connect(self._on_top_level_changed)
        self._dock_widget.dockLocationChanged.connect(self._on_dock_location_changed)
    
    def _install_mouse_event_filter(self):
        """安装鼠标事件过滤器，在拖动开始时保存状态"""
        self._dock_widget.installEventFilter(self)
    
    def save_original_dock_info(self, area):
        """
        保存创建时的原始停靠区域（永久缓存，不随拖动清空）
        
        Args:
            area: Qt.DockWidgetArea - 停靠区域
        """
        self._original_dock_area = area
    
    def _on_dock_location_changed(self, area):
        """停靠位置变化回调：保存最后停靠区域"""
        if area != Qt.DockWidgetArea.NoDockWidgetArea:
            self._last_docked_state.area = area
    
    def _on_top_level_changed(self, floating):
        """漂浮状态切换回调"""
        if floating:
            self._save_docked_state()
        else:
            QTimer.singleShot(50, self._restore_to_docked_position)
    
    def save_current_state_before_toggle(self):
        """
        在双击切换前手动保存当前状态
        
        必须在调用 setFloating() 之前调用，避免Qt清空缓存后保存失败
        """
        if self._dock_widget.isFloating():
            geo = self._dock_widget.geometry()
            self._last_floating_geometry = FloatingGeometry(
                geo.x(), geo.y(), geo.width(), geo.height()
            )
        else:
            parent = self._dock_widget.parent()
            while parent and not isinstance(parent, QMainWindow):
                parent = parent.parent()
            if parent:
                area = parent.dockWidgetArea(self._dock_widget)
                if area != Qt.DockWidgetArea.NoDockWidgetArea:
                    self._last_docked_state.area = area
    
    def eventFilter(self, obj, event):
        """
        事件过滤器：在拖动开始时（鼠标按下）保存当前停靠状态
        
        当用户拖动dock从主窗口分离时，在鼠标按下时就保存状态，
        这样即使Qt在拖动过程中清空缓存，我们也有之前保存的状态。
        """
        if obj == self._dock_widget:
            if event.type() == QEvent.MouseButtonPress:
                if not self._dock_widget.isFloating():
                    parent = self._dock_widget.parent()
                    while parent and not isinstance(parent, QMainWindow):
                        parent = parent.parent()
                    if parent:
                        area = parent.dockWidgetArea(self._dock_widget)
                        if area != Qt.DockWidgetArea.NoDockWidgetArea:
                            self._last_docked_state.area = area
        
        return super().eventFilter(obj, event)
    
    def _save_docked_state(self):
        """保存当前停靠状态（切换到悬浮前调用）"""
        parent = self._dock_widget.parent()
        while parent and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        
        if parent:
            area = parent.dockWidgetArea(self._dock_widget)
            if area != Qt.DockWidgetArea.NoDockWidgetArea:
                self._last_docked_state.area = area
    
    def _save_floating_geometry(self):
        """保存当前悬浮几何（切换到停靠前调用）"""
        if self._dock_widget.isFloating():
            geo = self._dock_widget.geometry()
            self._last_floating_geometry = FloatingGeometry(
                geo.x(), geo.y(), geo.width(), geo.height()
            )
    
    def _restore_to_docked_position(self):
        """恢复到上次停靠位置（带重试机制）"""
        parent = self._dock_widget.parent()
        while parent and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        
        if parent:
            area = self._original_dock_area if self._original_dock_area is not None else self._last_docked_state.area
            if area is not None and area != Qt.DockWidgetArea.NoDockWidgetArea:
                current_area = parent.dockWidgetArea(self._dock_widget)
                if current_area != area:
                    parent.removeDockWidget(self._dock_widget)
                    parent.addDockWidget(area, self._dock_widget)
                    parent.centralWidget().updateGeometry()
                    parent.update()
                    parent.repaint()
                    QApplication.processEvents()
                    
                    QTimer.singleShot(50, lambda: self._verify_and_restore(parent, area))
    
    def _verify_and_restore(self, parent, area):
        """验证并再次恢复dock位置"""
        current_area = parent.dockWidgetArea(self._dock_widget)
        if current_area != area:
            parent.removeDockWidget(self._dock_widget)
            parent.addDockWidget(area, self._dock_widget)
            parent.setCentralWidget(parent.centralWidget())
            parent.centralWidget().updateGeometry()
            parent.update()
            parent.repaint()
            QApplication.processEvents()
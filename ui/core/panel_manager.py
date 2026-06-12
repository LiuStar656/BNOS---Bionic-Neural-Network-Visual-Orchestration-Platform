"""
面板管理器，负责管理各种面板的创建、显示和持久化
"""
from typing import Dict, Type, Callable, Any, Optional
from PyQt6.QtWidgets import QWidget, QDockWidget
from PyQt6.QtCore import Qt
from pathlib import Path
from ui.core.logger import logger
import json


class PanelDescriptor:
    """面板描述符"""
    def __init__(
        self,
        key: str,
        factory: Callable[[Any], QWidget],
        area: Qt.DockWidgetArea = Qt.DockWidgetArea.LeftDockWidgetArea,
        default_visible: bool = False,
        title: str = ""
    ):
        self.key = key
        self.factory = factory
        self.area = area
        self.default_visible = default_visible
        self.title = title


class PanelRegistry:
    """面板注册表"""
    def __init__(self):
        self._panels: Dict[str, PanelDescriptor] = {}
        self._instances: Dict[str, QWidget] = {}

    def register(self, descriptor: PanelDescriptor):
        self._panels[descriptor.key] = descriptor

    def get_descriptor(self, key: str) -> Optional[PanelDescriptor]:
        return self._panels.get(key)

    def create_instance(self, key: str, parent) -> Optional[QWidget]:
        descriptor = self._panels.get(key)
        if descriptor:
            panel = descriptor.factory(parent)
            self._instances[key] = panel
            return panel
        return None

    def get_instance(self, key: str) -> Optional[QWidget]:
        return self._instances.get(key)

    def get_all_keys(self) -> list:
        return list(self._panels.keys())


class PanelManager:
    """面板管理器"""

    def __init__(self, main_window, config_path: Path):
        self.main_window = main_window
        self.config_path = config_path
        self.registry = PanelRegistry()
        self.dock_widgets: Dict[str, QDockWidget] = {}
        self._register_default_panels()

    def _register_default_panels(self):
        from ui.panels.node_list_dock import NodeListDockPanel
        from ui.panels.resource_monitor_dock import ResourceMonitorDock
        from ui.panels.node_monitor_dock import NodeMonitorDock

        self.registry.register(PanelDescriptor(
            key="node_list",
            factory=lambda p: NodeListDockPanel(p),
            area=Qt.DockWidgetArea.LeftDockWidgetArea,
            default_visible=True,
            title="节点列表"
        ))
        self.registry.register(PanelDescriptor(
            key="resource_monitor",
            factory=lambda p: ResourceMonitorDock(p),
            area=Qt.DockWidgetArea.RightDockWidgetArea,
            default_visible=False,
            title="资源监控"
        ))
        self.registry.register(PanelDescriptor(
            key="node_monitor",
            factory=lambda p: NodeMonitorDock(p),
            area=Qt.DockWidgetArea.RightDockWidgetArea,
            default_visible=False,
            title="节点监控"
        ))

    def toggle_panel(self, key: str, visible: bool = None):
        if key in self.dock_widgets:
            dock_widget = self.dock_widgets[key]
            if visible is None:
                visible = not dock_widget.isVisible()
            dock_widget.setVisible(visible)
        else:
            panel = self.registry.create_instance(key, self.main_window)
            if panel:
                dock_widget = QDockWidget(self.registry.get_descriptor(key).title, self.main_window)
                dock_widget.setWidget(panel)
                descriptor = self.registry.get_descriptor(key)
                self.main_window.addDockWidget(descriptor.area, dock_widget)
                dock_widget.setVisible(visible if visible is not None else descriptor.default_visible)
                self.dock_widgets[key] = dock_widget
                dock_widget.visibilityChanged.connect(
                    lambda: self._on_panel_visibility_changed(key, dock_widget.isVisible())
                )
        self.save_panel_states()

    def _on_panel_visibility_changed(self, key: str, visible: bool):
        self.save_panel_states()

    def load_panel_states(self):
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                panel_states = config.get('panel_visibility', {})
                for key, visible in panel_states.items():
                    if key in self.registry.get_all_keys():
                        self.toggle_panel(key, visible)
        except Exception as e:
            logger.error("加载面板状态失败: %s", e)

    def save_panel_states(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            panel_states = {}
            for key in self.registry.get_all_keys():
                if key in self.dock_widgets:
                    panel_states[key] = self.dock_widgets[key].isVisible()
            config = {}
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            config['panel_visibility'] = panel_states
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("保存面板状态失败: %s", e)

    def show_panel(self, key: str):
        self.toggle_panel(key, True)

    def hide_panel(self, key: str):
        self.toggle_panel(key, False)

    def is_panel_visible(self, key: str) -> bool:
        if key in self.dock_widgets:
            return self.dock_widgets[key].isVisible()
        return False

"""
Dock位置管理器 - 使用 JSON 文件持久化停靠/悬浮坐标

核心设计：
1. 每次 dockLocationChanged（停靠区域变化）时立即写入 JSON 文件
2. 每次浮动窗口拖动时定时保存最新坐标
3. 双击回到停靠状态时从 JSON 文件读取目标区域，不受 Qt 缓存清空影响
4. 恢复过程中屏蔽 dockLocationChanged 信号，防止被 Qt 自动分配的区域覆盖
"""
import json
import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QObject
from PySide6.QtWidgets import QMainWindow, QApplication


class DockPositionManager(QObject):
    """Dock 位置管理器 - 持久化坐标方案"""

    _CONFIG_DIR = Path(os.getcwd()) / ".bnos"
    _CONFIG_FILE = _CONFIG_DIR / "dock_positions.json"

    def __init__(self, dock_widget):
        super().__init__()
        self._dock_widget = dock_widget
        self._dock_id = dock_widget.objectName() or dock_widget.windowTitle()
        self._original_dock_area = None
        self._float_tracker = None
        self._block_persist = False  # 恢复期间屏蔽自动持久化

        self._connect_signals()
        self._ensure_config_dir()

    # ── 初始化 ──

    @classmethod
    def _ensure_config_dir(cls):
        cls._CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def _connect_signals(self):
        self._dock_widget.topLevelChanged.connect(self._on_top_level_changed)
        self._dock_widget.dockLocationChanged.connect(self._on_dock_location_changed)

    def save_original_dock_info(self, area):
        self._original_dock_area = area

    # ── JSON 持久化 ──

    @classmethod
    def _load_all_positions(cls):
        try:
            if cls._CONFIG_FILE.exists():
                return json.loads(cls._CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {}

    @classmethod
    def _save_all_positions(cls, data):
        try:
            cls._CONFIG_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception:
            pass

    def _persist_docked_area(self, area):
        if self._block_persist:
            return
        data = self._load_all_positions()
        entry = data.get(self._dock_id, {})
        entry["docked_area"] = area.value
        data[self._dock_id] = entry
        self._save_all_positions(data)

    def _persist_floating_geometry(self, geo):
        data = self._load_all_positions()
        entry = data.get(self._dock_id, {})
        entry["floating"] = {
            "x": geo.x(),
            "y": geo.y(),
            "width": geo.width(),
            "height": geo.height()
        }
        data[self._dock_id] = entry
        self._save_all_positions(data)

    def _get_persisted_docked_area(self):
        data = self._load_all_positions()
        entry = data.get(self._dock_id, {})
        area_val = entry.get("docked_area")
        if area_val is not None:
            return Qt.DockWidgetArea(area_val)
        return None

    # ── 公共接口 ──

    def save_current_state_before_toggle(self):
        """
        在 setFloating() 之前调用，保存当前状态到 JSON。
        此时 Qt 尚未清空缓存，dockWidgetArea() 仍然有效。
        同时开启持久化屏蔽，防止 setFloating(False) 触发的
        dockLocationChanged 覆盖正确的停靠区域。
        """
        if self._dock_widget.isFloating():
            self._persist_floating_geometry(self._dock_widget.geometry())
            self._block_persist = True  # 即将嵌入，屏蔽后续的自动持久化
        else:
            parent = self._dock_widget.parent()
            while parent and not isinstance(parent, QMainWindow):
                parent = parent.parent()
            if parent:
                area = parent.dockWidgetArea(self._dock_widget)
                if area != Qt.DockWidgetArea.NoDockWidgetArea:
                    self._persist_docked_area(area)

    def unblock_persist(self):
        """恢复完成后调用，重新允许自动持久化"""
        self._block_persist = False

    # ── 信号回调 ──

    def _on_dock_location_changed(self, area):
        if area != Qt.DockWidgetArea.NoDockWidgetArea and not self._block_persist:
            self._persist_docked_area(area)

    def _on_top_level_changed(self, floating):
        if floating:
            self._start_float_tracking()
        else:
            self._stop_float_tracking()

    # ── 浮动位置追踪 ──

    def _start_float_tracking(self):
        if self._float_tracker is None:
            self._float_tracker = QTimer(self)
            self._float_tracker.timeout.connect(self._track_float_position)
        self._float_tracker.start(500)

    def _stop_float_tracking(self):
        if self._float_tracker:
            self._float_tracker.stop()
        if self._dock_widget.isFloating():
            self._persist_floating_geometry(self._dock_widget.geometry())

    def _track_float_position(self):
        if self._dock_widget.isFloating():
            self._persist_floating_geometry(self._dock_widget.geometry())

    # ── 恢复到停靠位置 ──

    def restore_to_docked_position(self, attempt=0):
        """
        绕过 setFloating(False) 的平移动画。
        关键：先 setFloating(False) 转换内部状态，再用 removeDockWidget+addDockWidget
        强制覆盖目标区域。用 setUpdatesEnabled 抑制动画。
        """
        main_win = self._find_main_window()
        if not main_win:
            if attempt < 5:
                QTimer.singleShot(80, lambda: self.restore_to_docked_position(attempt + 1))
            else:
                self._block_persist = False
            return

        area = self._original_dock_area
        if area is None:
            area = self._get_persisted_docked_area()

        if area is None or area == Qt.DockWidgetArea.NoDockWidgetArea:
            self._block_persist = False
            return

        main_win.setUpdatesEnabled(False)
        self._dock_widget.hide()
        self._dock_widget.setFloating(False)
        QApplication.processEvents()  # 清空 setFloating 触发的布局请求
        main_win.removeDockWidget(self._dock_widget)
        main_win.addDockWidget(area, self._dock_widget)
        QApplication.processEvents()  # 处理 addDockWidget 的布局请求
        self._dock_widget.show()
        self._dock_widget.raise_()
        main_win.setUpdatesEnabled(True)

        main_win.centralWidget().updateGeometry()
        main_win.update()
        main_win.repaint()
        QApplication.processEvents()

        self._block_persist = False

    def _find_main_window(self):
        """找到所属的 QMainWindow"""
        # 先通过 parent() 找（浮动时 QMainWindow 仍是 QObject parent）
        p = self._dock_widget.parent()
        while p:
            if isinstance(p, QMainWindow):
                return p
            p = p.parent()
        # 再通过顶层窗口找
        top = self._dock_widget.window()
        if isinstance(top, QMainWindow):
            return top
        return None

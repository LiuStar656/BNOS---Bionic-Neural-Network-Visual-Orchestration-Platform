"""
CanvasHost - 画布宿主窗口（QMainWindow）

严格按PS布局设计：
1. 作为主窗口的中央控件，与左右Dock面板平级
2. 自身固定不动，内部全域作为画布专属Dock停靠区
3. 每个画布都是独立的BNOSDock，支持停靠、标签、悬浮、独立拖出
4. 与主窗口面板Dock完全隔离，永不混叠
5. 画布Dock强制停靠在顶部，标签页显示在顶部

【架构重构】新增空白缓冲层设计：
- 启动时显示空白缓冲层（BlankPlaceholder），无任何画布
- 用户新建/打开项目时才创建画布Dock
- 关闭所有画布后自动切回缓冲层

【增强功能】独立画布数据管理：
- 每个画布维护独立的nodes_data和connections
- 画布切换时同步对应数据到主窗口
"""
import os
import json
from PySide6.QtWidgets import (
    QMainWindow, QDockWidget, QTabWidget, QWidget, QVBoxLayout, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from ui.core.logger import logger
from ui.core.i18n import t
from ui.canvas import NodeCanvas
from ui.core.bnos_dock import BnosDock
from ui.core.terminal.terminal_dock import TerminalDock


class BlankPlaceholder(QWidget):
    """空白缓冲层 - 纯空白占位，无任何业务逻辑"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """设置UI - 深色背景，中央显示提示文字"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Logo标签
        self._logo_label = QLabel()
        self._logo_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 30px;
                font-weight: bold;
            }
        """)
        
        # 设置BNOS ASCII logo
        ascii_logo = [
            " █████╗     ███╗  ██╗     █████╗     ██████╗ ",
            " ██╔══██╗   ████╗ ██║    ██╔══██╗   ██╔════╝ ",
            "██████╔╝   ██╔██╗██║    ██║  ██║   ╚█████╗  ",
            " ██╔══██╗   ██║╚████║    ██║  ██║    ╚═══██╗ ",
            " ██████╔╝   ██║ ╚███║    ╚█████╔╝   ██████╔╝ ",
            "  ╚═════╝    ╚═╝  ╚══╝     ╚════╝    ╚═════╝  ",
        ]
        logo_text = '\n'.join(ascii_logo)
        self._logo_label.setText(logo_text)
        self._logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._logo_label)
        
        # 副标题标签
        self._subtitle_label = QLabel("Bionic Neural Network Program Operating System")
        self._subtitle_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                font-size: 20px;
                font-weight: normal;
            }
        """)
        self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._subtitle_label)
        
        # 提示标签
        self._hint_label = QLabel(t("k_canvas_empty_hint"))
        self._hint_label.setStyleSheet("""
            QLabel {
                color: #4a4a4a;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._hint_label)
        
        # 设置深色背景
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)


class CanvasHost(QMainWindow):
    """画布宿主窗口 - 作为Canvas专属的Dock停靠容器（固定不动）"""
    
    canvas_changed = Signal(object)  # 当前激活的画布变化
    canvas_focused = Signal(object)  # 画布获得焦点
    all_canvases_closed = Signal()   # 所有画布已关闭
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent_window = parent
        
        # 核心配置：无边框样式，作为内嵌窗口使用
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # 关闭标志，防止关闭过程中的 hideEvent 覆盖持久化状态
        self._is_closing = False
        
        # 画布Dock存储
        self._canvas_docks = []
        self._active_canvas = None
        
        # 画布数据存储：每个画布独立维护其节点数据和连接
        self._canvas_data_map = {}  # {canvas: {'nodes_data': {}, 'connections': []}}
        
        # 空白缓冲层
        self._blank_placeholder = None
        
        # 初始化时显示空白缓冲层，不创建任何画布
        self._init_blank_placeholder()
        
        # 设置样式
        self._setup_styles()
        
        # 标记终端是否已初始化
        self._terminal_initialized = False
        
        # 设置Dock选项以支持标签页堆叠（将在创建第一个画布时启用）
        # 初始时保持默认设置，因为空白缓冲层作为中央控件
        
        # 监听焦点变化，以便检测用户切换画布
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            app.focusChanged.connect(self._on_focus_changed)
        
        # 连接画布改变信号，更新终端
        self.canvas_changed.connect(self._update_terminal_on_canvas_change)
    
    def _setup_styles(self):
        """设置CanvasHost样式 - 深色背景作为画布区域"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                border: none;
            }
        """)
    
    def _init_blank_placeholder(self):
        """初始化空白缓冲层 - 作为默认显示"""
        # 清空中央控件
        if self.centralWidget():
            self.centralWidget().deleteLater()
        
        # 创建空白缓冲层
        self._blank_placeholder = BlankPlaceholder(self)
        self.setCentralWidget(self._blank_placeholder)
        
        logger.info("CanvasHost: 已初始化空白缓冲层")
    
    def _remove_blank_placeholder(self):
        """移除空白缓冲层 - 在创建第一个画布时调用
        
        关键修复：必须设置一个透明占位控件作为中央控件，否则 Qt 的 dock widget
        停靠系统无法正确显示画布（因为 dock widget 需要围绕中央控件停靠）。
        首次打开项目时（blank_placeholder 仍存在）才会走这个路径；之后 canvas dock
        已存在，中央控件也已设置，不会再触发这里。
        """
        if self._blank_placeholder and self._blank_placeholder.isVisible():
            self.setCentralWidget(None)
            self._blank_placeholder.deleteLater()
            self._blank_placeholder = None
            
            # ✅ 创建透明中央占位控件（必须有中央控件，dock widget 才能正确停靠）
            # 使用一个空的 QWidget，无布局，无内容，不占用实际显示空间，仅为了让
            # Qt 的 dock 系统正确工作
            central_placeholder = QWidget(self)
            central_placeholder.setStyleSheet("background: transparent;")
            central_placeholder.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            central_placeholder.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
            central_placeholder.setFixedSize(0, 0)
            central_placeholder.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
            central_placeholder.setObjectName("canvas_host_central_placeholder")
            self.setCentralWidget(central_placeholder)
            
            # 启用Dock停靠功能（PS布局要求）
            self.setTabPosition(Qt.DockWidgetArea.AllDockWidgetAreas, QTabWidget.TabPosition.North)
            self.setDockOptions(
                QMainWindow.DockOption.AllowTabbedDocks |
                QMainWindow.DockOption.AllowNestedDocks
            )
            
            logger.info("CanvasHost: 空白缓冲层已移除，启用Dock停靠")
    
    def _create_canvas_dock(self, name=None, project_path=None):
        """创建独立的画布Dock - 每个画布都是独立的QDockWidget，强制停靠在顶部"""
        # 1. 如果还显示缓冲层，先移除
        if self._blank_placeholder:
            self._remove_blank_placeholder()
        
        # 2. 实例化 NodeCanvas
        canvas = NodeCanvas(self)
        canvas.parent_window = self._parent_window

        # ===== 诊断: 检查 parent_window.nodes_data 是否有数据 =====
        pw_nodes_data_count = 0
        if self._parent_window is not None and hasattr(self._parent_window, 'nodes_data'):
            pw_nodes_data_count = len(self._parent_window.nodes_data)
        logger.info(
            "[CanvasHost] 创建画布前检查: parent_window=%s, nodes_data=%d个节点, project_path=%s",
            "OK" if self._parent_window is not None else "NONE",
            pw_nodes_data_count,
            project_path
        )

        # 初始化画布独立数据
        canvas_data = {
            'nodes_data': {},
            'connections': [],
            'project_path': project_path
        }

        # 如果有项目路径，加载布局
        if project_path:
            logger.info("[CanvasHost] 调用 canvas.load_layout(%s)", project_path)
            canvas.load_layout(project_path)
            logger.info("[CanvasHost] load_layout完成，画布上有 %d 个节点", len(canvas.nodes))

        # 3. 用 BNOSDock 封装画布
        dock_name = name if name else f"{t('k_canvas')} {len(self._canvas_docks) + 1}"
        canvas_dock = BnosDock(dock_name, self)
        canvas_dock.set_content_widget(canvas)

        # 4. 设置画布Dock特性
        canvas_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        # 5. 只允许停靠在顶部区域
        canvas_dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea)

        # 6. 添加到 CanvasHost
        if self._canvas_docks:
            first_dock = self._canvas_docks[0]
            self.tabifyDockWidget(first_dock, canvas_dock)
            logger.info("[CanvasHost] 画布已合并到标签页")
        else:
            # 首个画布Dock — addDockWidget 不自动激活 tab
            self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, canvas_dock)
            logger.info("[CanvasHost] 首个画布已停靠到顶部")
        
        canvas_dock.save_original_dock_info(Qt.DockWidgetArea.TopDockWidgetArea)

        # ✅ 强制显示（解决首次打开项目时画布不显示的问题）
        canvas_dock.show()
        canvas_dock.raise_()
        canvas.show()
        canvas.raise_()
        canvas.setFocus()
        logger.info("[CanvasHost] 画布Dock已强制显示")
        
        # 7. 添加到画布Dock列表
        self._canvas_docks.append(canvas_dock)
        
        # 8. 存储画布数据
        self._canvas_data_map[canvas] = canvas_data
        
        # 9. 设置为活动画布
        self._active_canvas = canvas
        
        # 10. 如果是第一个画布，初始化终端 Dock（确保画布先加载）
        if len(self._canvas_docks) == 1:
            self._init_terminal_dock()
        
        # 11. 连接信号 - 监听关闭事件和焦点变化事件
        canvas_dock.closed.connect(lambda dock: self._on_canvas_dock_closed(dock))
        canvas_dock.dockLocationChanged.connect(lambda area, c=canvas: self._on_canvas_location_changed(area, c))
        canvas_dock.visibilityChanged.connect(lambda visible, c=canvas: self._on_canvas_visibility_changed(visible, c))
        
        logger.info(f"CanvasHost: 画布Dock '{dock_name}' 已创建（顶部停靠）")
        return canvas_dock, canvas
    
    # 说明：_load_project_data 已移除 — 该函数从未被调用，且节点扫描已由
    # ProjectLoadWorker 在后台线程完成，其结果通过 parent_window.nodes_data
    # 传递给 canvas.load_layout 使用。

    def get_canvas_data(self, canvas):
        """获取指定画布的数据"""
        return self._canvas_data_map.get(canvas, {'nodes_data': {}, 'connections': [], 'project_path': None})
    
    def set_canvas_data(self, canvas, nodes_data, connections):
        """设置指定画布的数据"""
        if canvas in self._canvas_data_map:
            self._canvas_data_map[canvas]['nodes_data'] = nodes_data
            self._canvas_data_map[canvas]['connections'] = connections
        else:
            self._canvas_data_map[canvas] = {
                'nodes_data': nodes_data,
                'connections': connections,
                'project_path': getattr(canvas, 'current_project_path', None)
            }
    
    def sync_canvas_data_to_main_window(self, canvas):
        """将指定画布的数据同步到主窗口"""
        if self._parent_window and canvas in self._canvas_data_map:
            canvas_data = self._canvas_data_map[canvas]
            # 同步数据到主窗口
            self._parent_window.nodes_data = canvas_data['nodes_data'].copy()
            self._parent_window.connections = canvas_data['connections'][:]
            self._parent_window.current_project_path = canvas_data['project_path']
            # 刷新面板
            self._parent_window._refresh_panels()
    
    def update_canvas_data_from_main_window(self, canvas):
        """从主窗口更新指定画布的数据"""
        if self._parent_window and canvas in self._canvas_data_map:
            self._canvas_data_map[canvas]['nodes_data'] = self._parent_window.nodes_data.copy()
            self._canvas_data_map[canvas]['connections'] = self._parent_window.connections[:]
            self._canvas_data_map[canvas]['project_path'] = self._parent_window.current_project_path
    
    def sync_main_window_data_to_canvas(self, nodes_data=None, connections=None):
        """将主窗口的当前数据同步到活动画布（用于数据保存）"""
        if self._parent_window and self._active_canvas and self._active_canvas in self._canvas_data_map:
            # 如果提供了数据，则使用提供的数据，否则使用主窗口的当前数据
            if nodes_data is not None:
                self._canvas_data_map[self._active_canvas]['nodes_data'] = nodes_data
            else:
                self._canvas_data_map[self._active_canvas]['nodes_data'] = self._parent_window.nodes_data.copy()
                
            if connections is not None:
                self._canvas_data_map[self._active_canvas]['connections'] = connections
            else:
                self._canvas_data_map[self._active_canvas]['connections'] = self._parent_window.connections[:]
                
            self._canvas_data_map[self._active_canvas]['project_path'] = self._parent_window.current_project_path
    
    def _on_canvas_dock_closed(self, canvas_dock):
        """画布Dock关闭事件 - 彻底销毁画布、项目实例与节点进程"""
        if canvas_dock not in self._canvas_docks:
            return
        
        # 1. 获取画布内容
        canvas = canvas_dock.get_content_widget()
        
        # 1.5. 在关闭前保存当前画布数据到主窗口（如果这是活动画布）
        if canvas == self._active_canvas and self._parent_window:
            self.update_canvas_data_from_main_window(canvas)
        
        # 2. 停止画布上所有节点进程（如果有）
        if canvas and hasattr(canvas, 'stop_all_nodes'):
            canvas.stop_all_nodes()
        
        # 3. 从列表中移除
        self._canvas_docks.remove(canvas_dock)
        
        # 4. 从数据映射中移除
        if canvas in self._canvas_data_map:
            del self._canvas_data_map[canvas]
        
        # 5. 彻底销毁画布Dock
        self.removeDockWidget(canvas_dock)
        canvas_dock.deleteLater()
        
        # 6. 更新活动画布
        if self._canvas_docks:
            # 还有其他画布，激活下一个
            last_dock = self._canvas_docks[-1]
            self._active_canvas = last_dock.get_content_widget()
            self.canvas_changed.emit(self._active_canvas)
        else:
            # 所有画布都关闭了，回到空白缓冲层
            self._active_canvas = None
            self._init_blank_placeholder()
            self.all_canvases_closed.emit()
            
            logger.info("CanvasHost: 所有画布已关闭，恢复空白缓冲层")
        
        logger.info(f"CanvasHost: 画布Dock已彻底销毁，剩余画布数: {len(self._canvas_docks)}")
    
    def add_canvas_dock(self, name=None, project_path=None):
        """添加新的独立画布Dock"""
        canvas_dock, canvas = self._create_canvas_dock(name, project_path)
        
        # 【关键】先同步主窗口数据到画布存储，再发 canvas_changed 信号
        # 否则 _on_canvas_changed → sync_canvas_data_to_main_window 会拿到空的初始化数据
        if self._parent_window:
            self.update_canvas_data_from_main_window(canvas)
        
        # 更新活动画布
        self._active_canvas = canvas
        # 发出画布更改信号，这会触发主窗口同步数据
        self.canvas_changed.emit(canvas)
        
        return canvas
    
    def _on_canvas_visibility_changed(self, visible, canvas):
        """画布可见性变化 - 触发焦点信号"""
        if visible and canvas:
            # 只有当画布变为可见且不是当前活动画布时，才更新活动画布
            if self._active_canvas != canvas:
                self._active_canvas = canvas
                self.canvas_changed.emit(canvas)  # 使用canvas_changed而不是canvas_focused，保持一致性

    def _on_canvas_location_changed(self, area, canvas):
        """画布停靠位置变化 - 当用户拖动标签或切换标签时触发"""
        # 当画布位置改变时，通常意味着用户进行了交互，将其设为活动画布
        if canvas:
            if self._active_canvas != canvas:
                self._active_canvas = canvas
                self.canvas_changed.emit(canvas)
    
    def _on_focus_changed(self, old, new):
        """焦点变化事件 - 检测用户是否切换到不同的画布"""
        # 检查新焦点是否在某个画布或其子部件中
        current_widget = new
        focused_canvas = None
        
        while current_widget:
            # 检查是否是NodeCanvas或其子类
            if hasattr(current_widget, '__class__') and 'NodeCanvas' in [cls.__name__ for cls in current_widget.__class__.__mro__]:
                focused_canvas = current_widget
                break
            current_widget = current_widget.parent()
        
        # 如果焦点在某个画布上，且该画布不是当前活动画布，则更新活动画布
        if focused_canvas and focused_canvas != self._active_canvas:
            self._active_canvas = focused_canvas
            self.canvas_changed.emit(focused_canvas)

    def get_active_canvas(self):
        """获取当前活动画布"""
        return self._active_canvas
    
    def get_all_canvases(self):
        """获取所有画布"""
        canvases = []
        for dock in self._canvas_docks:
            content = dock.get_content_widget()
            if isinstance(content, NodeCanvas):
                canvases.append(content)
        return canvases
    
    def get_canvas_count(self):
        """获取画布数量"""
        return len(self._canvas_docks)
    
    def is_project_open(self, project_path):
        """检查项目是否已经打开"""
        if not project_path:
            return False

        # 标准化路径以确保比较准确
        normalized_path = os.path.normpath(os.path.abspath(project_path))

        for canvas in self.get_all_canvases():
            # 检查画布数据中的项目路径
            canvas_data = self.get_canvas_data(canvas)
            canvas_project_path = canvas_data.get('project_path')

            if canvas_project_path:
                normalized_canvas_path = os.path.normpath(os.path.abspath(canvas_project_path))
                if normalized_path == normalized_canvas_path:
                    return True

        return False

    def remove_canvas_dock_by_path(self, project_path):
        """根据项目路径移除对应画布 dock"""
        if not project_path:
            return

        normalized_path = os.path.normpath(os.path.abspath(project_path))
        docks_to_remove = []

        for dock in self._canvas_docks:
            content = dock.get_content_widget()
            if isinstance(content, NodeCanvas):
                canvas_data = self.get_canvas_data(content)
                canvas_project_path = canvas_data.get('project_path')
                if canvas_project_path:
                    if os.path.normpath(os.path.abspath(canvas_project_path)) == normalized_path:
                        docks_to_remove.append(dock)

        for dock in docks_to_remove:
            try:
                self.removeDockWidget(dock)
                dock.setParent(None)
                dock.deleteLater()
                if dock in self._canvas_docks:
                    self._canvas_docks.remove(dock)
                # 清理 canvas 数据映射
                for key in list(self._canvas_data_map.keys()):
                    try:
                        if key == dock or (hasattr(dock, 'get_content_widget') and
                                           key == dock.get_content_widget()):
                            del self._canvas_data_map[key]
                    except Exception:
                        pass
                logger.info("[CanvasHost] 已移除画布 dock: %s", project_path)
            except Exception as e:
                logger.warning("[CanvasHost] 移除画布 dock 失败: %s", e)
    
    def get_open_projects(self):
        """获取所有已打开的项目路径"""
        projects = []
        for canvas in self.get_all_canvases():
            canvas_data = self.get_canvas_data(canvas)
            project_path = canvas_data.get('project_path')
            if project_path and project_path not in projects:
                projects.append(project_path)
        return projects
    
    def sync_project_data(self, project_path, nodes_data):
        """同步项目数据到所有画布"""
        for canvas in self.get_all_canvases():
            canvas.current_project_path = project_path
            if hasattr(canvas, 'nodes_data'):
                canvas.nodes_data = nodes_data
            canvas.refresh_nodes()
    
    def save_all_layouts(self, project_path):
        """保存所有画布布局"""
        for canvas in self.get_all_canvases():
            canvas.save_layout(project_path)
    
    def load_layout_for_active(self, project_path):
        """为活动画布加载布局"""
        if self._active_canvas:
            self._active_canvas.load_layout(project_path)
    
    def closeEvent(self, event):
        """关闭事件 - 保存所有画布布局并清理终端进程"""
        # 设置关闭标志，防止 hideEvent 触发的 visibility_changed 信号覆盖持久化状态
        self._is_closing = True
        
        # 先清理终端进程，避免 QProcess: Destroyed while process is still running 警告
        if hasattr(self, '_terminal_dock') and self._terminal_dock:
            self._terminal_dock.stop_all_terminals()
        
        if self._parent_window and self._parent_window.current_project_path:
            self.save_all_layouts(self._parent_window.current_project_path)
        super().closeEvent(event)
    
    def is_showing_placeholder(self):
        """是否显示空白缓冲层"""
        return self._blank_placeholder is not None
    
    def _ensure_terminal_initialized(self):
        """确保终端已初始化（仅第一次调用时真正初始化）"""
        if self._terminal_initialized:
            return
        self._init_terminal_dock()
    
    def _init_terminal_dock(self):
        """初始化终端 Dock，停靠在底部区域"""
        if self._terminal_initialized:
            return
            
        self._terminal_dock = TerminalDock(self, self._parent_window)
        
        # 停靠在底部区域
        self.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea, 
            self._terminal_dock
        )
        self._terminal_dock.save_original_dock_info(Qt.DockWidgetArea.BottomDockWidgetArea)
        
        # 默认先隐藏（不触发持久化保存，因为恢复状态在之后执行）
        self._terminal_dock.hide()
        
        # 延迟连接可见性信号，避免初始化阶段的 hide() 覆盖持久化状态
        from PySide6.QtCore import QTimer
        QTimer.singleShot(650, self._connect_terminal_signals)
        
        self._terminal_initialized = True
        logger.info("CanvasHost: 终端 Dock 已初始化")
    
    def _connect_terminal_signals(self):
        """延迟连接终端 Dock 的信号，避免与 restoreState 冲突"""
        if hasattr(self, '_terminal_dock') and self._terminal_dock:
            self._terminal_dock.visibility_changed.connect(
                self._on_terminal_visibility_changed
            )
    
    def _restore_panel_state(self):
        """从配置恢复终端 Dock 的状态"""
        if not self._parent_window:
            return
        
        visibility = self._parent_window.app_config.get('panel_visibility', {})
        show_terminal = visibility.get('terminal_dock', False)
        
        if show_terminal:
            self._terminal_dock.show()
    
    def _save_terminal_visibility_state(self, visible):
        """保存终端 Dock 的可见性状态"""
        from ui.core.logger import logger
        
        if getattr(self, '_is_closing', False):
            logger.info("[SKIP] _save_terminal_visibility_state: 正在关闭中，跳过保存 visible=%s", visible)
            return
        
        if not self._parent_window:
            return
        
        logger.info("[SAVE] _save_terminal_visibility_state: 保存 terminal_dock = %s", visible)
        visibility = self._parent_window.app_config.get('panel_visibility', {})
        visibility['terminal_dock'] = visible
        self._parent_window.app_config.set('panel_visibility', visibility)
        self._parent_window.app_config.save()
    
    def toggle_terminal(self):
        """切换终端 Dock 的显示/隐藏"""
        # 确保终端已初始化
        self._ensure_terminal_initialized()
        
        if self._terminal_dock.isVisible():
            self._terminal_dock.hide()
        else:
            self._terminal_dock.show()
    
    def _update_terminal_on_canvas_change(self, canvas):
        """画布改变时更新终端"""
        # 检查终端是否已初始化（在第一个画布创建时才初始化）
        if not hasattr(self, '_terminal_dock') or self._terminal_dock is None:
            return
        if hasattr(self._terminal_dock, 'sync_to_canvas'):
            self._terminal_dock.sync_to_canvas()
    
    def _on_terminal_visibility_changed(self, visible: bool):
        """终端可见性改变时处理：保存状态 + 更新菜单项"""
        from ui.core.logger import logger
        
        logger.info("🔔 _on_terminal_visibility_changed: visible=%s, is_closing=%s", 
                    visible, getattr(self, '_is_closing', False))
        
        # 关闭过程中不保存状态，防止 hideEvent 覆盖 closeEvent 中已保存的正确状态
        if getattr(self, '_is_closing', False):
            logger.info("[SKIP] _on_terminal_visibility_changed: 正在关闭中，跳过处理")
            return
        
        # 保存状态
        self._save_terminal_visibility_state(visible)
        
        # 更新菜单项
        if hasattr(self._parent_window, 'toggle_terminal_action'):
            self._parent_window.toggle_terminal_action.blockSignals(True)
            self._parent_window.toggle_terminal_action.setChecked(visible)
            self._parent_window.toggle_terminal_action.blockSignals(False)
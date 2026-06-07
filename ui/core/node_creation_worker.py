"""
节点创建异步工作线程 — 后台创建节点 + 浮动进度窗口
"""
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from ui.core.logger import logger


class NodeCreationWorker(QThread):
    """后台工作线程：负责创建节点"""
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, project_path, node_name, lang_key, display_language):
        super().__init__()
        self.project_path = project_path
        self.node_name = node_name
        self.lang_key = lang_key
        self.display_language = display_language

    def run(self):
        try:
            original_cwd = os.getcwd()
            nodes_dir = os.path.join(self.project_path, "nodes")

            if not os.path.exists(nodes_dir):
                os.makedirs(nodes_dir)

            os.chdir(nodes_dir)

            try:
                self.progress_signal.emit(f"开始创建 {self.display_language} 节点...")

                from ui.creators.node_creator_manager import NodeCreatorManager
                manager = NodeCreatorManager.get_instance()
                success = manager.create_node(self.lang_key, self.node_name)

                if success:
                    self.finished_signal.emit(True, f"{self.display_language} 节点 '{self.node_name}' 创建成功")
                else:
                    self.finished_signal.emit(False, f"{self.display_language} 节点创建失败")
            finally:
                os.chdir(original_cwd)
        except Exception as e:
            self.finished_signal.emit(False, f"创建节点异常: {str(e)}")
            import traceback
            traceback.print_exc()


class ProgressFloatingWindow(QWidget):
    """右上角浮动进度窗口 - 非模态，不阻塞画布操作"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # 添加 WindowStaysOnTopHint 确保进度窗口始终在最上层
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        # 添加WA_TranslucentBackground以支持rgba透明度
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)

        from ui.core.i18n import t
        self.title_label = QLabel(t("k_node_creating"))
        self.title_label.setStyleSheet("""
            QLabel { color: white; font-size: 14px; font-weight: bold; padding: 5px; }
        """)
        layout.addWidget(self.title_label)

        self.message_label = QLabel(t("k_node_init"))
        self.message_label.setStyleSheet("""
            QLabel { color: rgba(255, 255, 255, 0.9); font-size: 12px; padding: 5px; }
        """)
        layout.addWidget(self.message_label)

        self.setStyleSheet("""
            QWidget { background-color: rgba(33, 33, 33, 230); border-radius: 8px; }
        """)
        self.update_position()

    def update_position(self):
        """更新位置：与Toast通知对齐，放在CanvasHost内部右上角"""
        if self.parent():
            parent_window = self.parent()
            
            # 查找CanvasHost
            canvas_host = None
            if hasattr(parent_window, '_canvas_host'):
                canvas_host = parent_window._canvas_host
            
            if canvas_host:
                # 使用CanvasHost的位置和大小（画布区域）
                host_geo = canvas_host.geometry()
                host_pos = canvas_host.mapToGlobal(host_geo.topLeft())
                w = self.width() if self.width() > 0 else 250
                # 向右偏移10px，向下偏移35px（与Toast通知对齐）
                self.move(host_pos.x() + host_geo.width() - w - 10, host_pos.y() + 35)
            else:
                # 回退到主窗口右上角
                parent_rect = parent_window.geometry()
                w = self.width() if self.width() > 0 else 250
                self.move(parent_rect.right() - w - 10, parent_rect.top() + 35)


def start_async_node_creation(main_window, node_name, lang_key, display_language):
    """启动异步节点创建流程"""
    worker = NodeCreationWorker(
        main_window.current_project_path, node_name, lang_key, display_language
    )
    worker.setParent(main_window)
    main_window.node_creation_worker = worker

    progress_window = ProgressFloatingWindow(main_window)
    progress_window.show()

    def update_progress(message):
        if progress_window.isVisible():
            progress_window.message_label.setText(message)

    def creation_finished(success, message):
        if progress_window.isVisible():
            progress_window.close()
        if success:
            main_window.show_toast(message, "success")
            main_window.refresh_nodes()
            # 刷新所有节点列表面板（包括浮动面板和Dock面板）
            main_window._refresh_panels()
        else:
            main_window.show_toast(message, "error")

    worker.progress_signal.connect(update_progress)
    worker.finished_signal.connect(creation_finished)
    # 线程完成后自动删除
    worker.finished_signal.connect(worker.deleteLater)
    worker.start()
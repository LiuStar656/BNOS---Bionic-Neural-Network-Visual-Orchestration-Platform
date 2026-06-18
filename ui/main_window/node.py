"""
BNOS 主窗口节点控制模块

负责节点的创建、启动、停止等控制操作，包括：
- 节点创建（支持多种语言）
- 节点启动/停止（异步执行，支持队列调度）
- 节点导入/导出
- 节点状态同步
"""
from PySide6.QtCore import QTimer, QThread, Signal
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.node_process import start_node_process, stop_node_process, resolve_selected_node
from ui.core.node_control_service import NodeStatus, node_control_service
from ui.core.node_startup_queue import startup_queue, QueueStatus


class MainWindowNodeControlMixin:
    """节点控制Mixin - 处理节点的创建、启动、停止等操作"""

    def create_new_node(self):
        """创建新节点（默认Python）"""
        self.create_new_node_with_language("Python")

    def create_new_node_with_language(self, language):
        """使用指定语言创建新节点（供菜单调用）"""
        if not self.current_project_path:
            self.show_toast(t("k_project_no_project"), "warning")
            return

        if language not in ("Python", "Rust"):
            self.show_toast(t("k_node_lang_unsupported").replace("{lang}", language), "warning")
            return

        from ui.core.utils.dialog_utils import themed_input
        prompt = t("k_node_enter_name").replace("{lang}", language)
        node_name = themed_input(self, t("k_node_create"), prompt)
        if not node_name:
            return

        lang_map = {"Python": "python", "Rust": "rust"}
        lang_key = lang_map.get(language, language.lower())

        if not self.node_creator.has_creator(lang_key):
            self.show_toast(t("k_node_lang_unsupported").replace("{lang}", language), "warning")
            return

        self._start_async_node_creation(node_name, lang_key, language)

    def _start_async_node_creation(self, node_name, lang_key, display_language):
        from ui.core.node_creation_worker import start_async_node_creation
        start_async_node_creation(self, node_name, lang_key, display_language)

    def start_selected_node(self):
        """启动选中的节点"""
        selected = resolve_selected_node(self)
        if not selected:
            self.show_toast(t("k_node_select_first"), "warning")
            return
        self.start_selected_node_by_name(selected)

    def start_selected_node_by_name(self, node_name):
        """按名称启动节点（使用队列调度，不阻塞 GUI）"""
        if node_name not in self.nodes_data:
            return
        node_info = self.nodes_data[node_name]
        if node_info['status'] in ('running', 'idle'):
            self.show_toast(t("_k_node_running").format(name=node_name), "info")
            return

        if startup_queue.is_queued(node_name):
            status = startup_queue.get_status(node_name)
            if status == QueueStatus.BLOCKED:
                blocked_by = startup_queue.get_blocked_reason(node_name)
                self.show_toast(f"节点 {node_name} 已在队列中（等待: {', '.join(blocked_by)}）", "info")
            else:
                self.show_toast(f"节点 {node_name} 已在启动队列中", "info")
            return

        startup_queue.set_project_context(self.current_project_path, self.nodes_data, self.canvas)

        dependencies = []
        if self.canvas:
            dependencies = self.canvas.get_node_dependencies(node_name)

        success = startup_queue.enqueue(node_name, dependencies=dependencies)
        if success:
            self._setup_queue_event_handlers()
            self.node_list_panel.update_node_status(node_name, 'queued')
            if self.canvas:
                self.canvas.update_node_status(node_name, 'queued')
            if dependencies:
                self.show_toast(f"节点 {node_name} 已加入启动队列（等待: {', '.join(dependencies)}）", "info")
            else:
                self.show_toast(f"节点 {node_name} 已加入启动队列", "info")
        else:
            self.show_toast(f"加入队列失败", "error")

    def _setup_queue_event_handlers(self):
        """设置队列事件处理器（仅设置一次）"""
        if hasattr(self, '_queue_handlers_set') and self._queue_handlers_set:
            return

        startup_queue.on('node_starting', self._on_queue_node_starting)
        startup_queue.on('node_started', self._on_queue_node_started)
        startup_queue.on('node_failed', self._on_queue_node_failed)
        startup_queue.on('node_retry', self._on_queue_node_retry)
        startup_queue.on('node_blocked', self._on_queue_node_blocked)
        startup_queue.on('queue_empty', self._on_queue_empty)
        self._queue_handlers_set = True

    def _on_queue_node_starting(self, node_name):
        """队列节点开始启动"""
        logger.info(f"队列节点开始启动: {node_name}")
        self.node_list_panel.update_node_status(node_name, 'starting')
        if self.canvas:
            self.canvas.update_node_status(node_name, 'starting')
        self.show_toast(t("_k_node_starting").format(name=node_name), "info",
                        node_name=node_name, operation_type="start")

    def _on_queue_node_started(self, node_name):
        """队列节点启动成功"""
        logger.info(f"队列节点启动成功: {node_name}")
        self.node_list_panel.update_node_status(node_name, 'idle')
        if self.canvas:
            self.canvas.update_node_status(node_name, 'idle')
        self.show_toast(t("_k_node_started").format(name=node_name), "success",
                        node_name=node_name, operation_type="start")
        node_control_service._notify(node_name, NodeStatus.RUNNING)

    def _on_queue_node_failed(self, node_name, error):
        """队列节点启动失败"""
        logger.error(f"队列节点启动失败: {node_name} - {error}")
        self.node_list_panel.update_node_status(node_name, 'stopped')
        if self.canvas:
            self.canvas.update_node_status(node_name, 'stopped')
        from ui.core.utils.dialog_utils import themed_message
        themed_message(self, t("k_title_error"), t("_k_start_fail").format(err=error), "error")
        node_control_service._notify(node_name, NodeStatus.ERROR)

    def _on_queue_node_retry(self, node_name, retry_count):
        """队列节点准备重试"""
        logger.warning(f"队列节点准备重试 ({retry_count}): {node_name}")
        self.show_toast(f"节点 {node_name} 启动失败，正在重试 ({retry_count})...", "warning")

    def _on_queue_node_blocked(self, node_name, blocked_by):
        """队列节点被依赖阻塞"""
        logger.info(f"队列节点被阻塞: {node_name} 等待 {blocked_by}")
        self.node_list_panel.update_node_status(node_name, 'blocked')
        if self.canvas:
            self.canvas.update_node_status(node_name, 'blocked')
        self.show_toast(f"节点 {node_name} 等待依赖节点启动: {', '.join(blocked_by)}", "info")

    def _on_queue_empty(self):
        """队列处理完成"""
        logger.info("启动队列处理完成")
        self.show_toast("所有节点启动任务已完成", "success")

    def _start_node_async(self, node_name):
        """异步启动节点（使用后台线程执行，不阻塞GUI）"""
        if node_name not in self.nodes_data:
            return

        class StartNodeWorker(QThread):
            finished = Signal(bool, str)

            def __init__(self, node_info, parent=None):
                super().__init__(parent)
                self.node_info = node_info

            def run(self):
                success, err = start_node_process(self.node_info)
                self.finished.emit(success, err)

        node_info = self.nodes_data[node_name]
        worker = StartNodeWorker(node_info)

        self._node_start_workers.append(worker)

        def on_complete(success, err):
            if worker in self._node_start_workers:
                self._node_start_workers.remove(worker)

            if success:
                self.node_list_panel.update_node_status(node_name, 'idle')
                if self.canvas:
                    self.canvas.update_node_status(node_name, 'idle')
                self.show_toast(t("_k_node_started").format(name=node_name), "success",
                                node_name=node_name, operation_type="start")
                node_control_service._notify(node_name, NodeStatus.RUNNING)
            else:
                self.node_list_panel.update_node_status(node_name, 'stopped')
                if self.canvas:
                    self.canvas.update_node_status(node_name, 'stopped')
                from ui.core.utils.dialog_utils import themed_message
                themed_message(self, t("k_title_error"), t("_k_start_fail").format(err=err), "error")
                node_control_service._notify(node_name, NodeStatus.ERROR)

        worker.finished.connect(on_complete)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def stop_selected_node(self):
        """停止选中的节点"""
        selected = resolve_selected_node(self)
        if not selected:
            self.show_toast(t("k_node_select_first"), "warning")
            return
        self.stop_selected_node_by_name(selected)

    def stop_selected_node_by_name(self, node_name):
        """按名称停止节点（异步执行，不阻塞 GUI）"""
        if node_name not in self.nodes_data:
            return
        node_info = self.nodes_data[node_name]
        if node_info['status'] == 'stopped':
            self.show_toast(t("_k_node_not_running_toast").format(name=node_name), "info")
            return

        self.node_list_panel.update_node_status(node_name, 'stopping')
        if self.canvas:
            self.canvas.update_node_status(node_name, 'stopping')
        self.show_toast(t("_k_node_stopping").format(name=node_name), "info",
                        node_name=node_name, operation_type="stop")

        QTimer.singleShot(10, lambda: self._stop_node_async(node_name))

    def _stop_node_async(self, node_name):
        """异步停止节点（内部方法）"""
        if node_name not in self.nodes_data:
            return

        node_info = self.nodes_data[node_name]
        success, err_msg = stop_node_process(node_info)

        def on_complete():
            if success:
                self.node_list_panel.update_node_status(node_name, 'stopped')
                if self.canvas:
                    self.canvas.update_node_status(node_name, 'stopped')
                self.show_toast(t("_k_node_stopped").format(name=node_name), "success",
                                node_name=node_name, operation_type="stop")
                node_control_service._notify(node_name, NodeStatus.STOPPED)
            else:
                # 杀失败 → 保持原状态，让健康检查发现僵尸
                from ui.core.utils.dialog_utils import themed_message
                from ui.core.i18n import t as i18n_t
                themed_message(self, i18n_t("k_title_error"),
                               i18n_t("_k_stop_fail").format(name=node_name, err=err_msg or ""),
                               "error")
                node_control_service._notify(node_name, NodeStatus.ERROR)

        QTimer.singleShot(10, on_complete)

    def update_node_status(self, node_name, status):
        """更新节点状态并同步UI"""
        if node_name in self.nodes_data:
            self.nodes_data[node_name]['status'] = status
            if self.canvas:
                self.canvas.sync_node_display(node_name)
            self.node_list_panel.update_node_list(self.nodes_data)

    def export_node(self, node_name=None):
        """导出单个节点（支持从菜单调用时自动获取选中节点）"""
        if not node_name:
            selected = resolve_selected_node(self)
            if not selected:
                self.show_toast(t("k_node_select_first"), "warning")
                return
            node_name = selected

        from ui.core.import_export_manager import ImportExportManager
        manager = ImportExportManager(self)
        manager.export_node(node_name)

    def export_project(self):
        """导出整个项目"""
        from ui.core.import_export_manager import ImportExportManager
        manager = ImportExportManager(self)
        manager.export_project()

    def import_node(self):
        """导入节点"""
        from ui.core.import_export_manager import ImportExportManager
        manager = ImportExportManager(self)
        manager.import_node()

    def mount_external_node(self):
        from ui.core.external_node_manager import mount_node
        mount_node(self)

    def unmount_external_node(self, node_name: str):
        from ui.core.external_node_manager import unmount_node as _unmount_node
        _unmount_node(self, node_name)
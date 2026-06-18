"""
队列管理面板 - 提供节点启动队列的可视化管理界面
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QProgressBar, QGroupBox, QToolButton,
    QMenu, QAction
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from ui.core.logger import logger
from ui.core.node_startup_queue import startup_queue, QueueStatus


class QueueManagerPanel(QWidget):
    """队列管理面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._setup_event_handlers()
        self._update_timer = QTimer(self)
        self._update_timer.setInterval(1000)
        self._update_timer.timeout.connect(self._refresh_queue_display)
        self._update_timer.start()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        title_label = QLabel("启动队列")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title_label)

        self._stats_label = QLabel("0 个节点")
        self._stats_label.setStyleSheet("font-size: 12px; color: #888;")
        header_layout.addWidget(self._stats_label)
        header_layout.addStretch()

        self._pause_btn = QToolButton()
        self._pause_btn.setText("暂停")
        self._pause_btn.setCheckable(True)
        self._pause_btn.clicked.connect(self._toggle_pause)
        header_layout.addWidget(self._pause_btn)

        self._clear_btn = QToolButton()
        self._clear_btn.setText("清空")
        self._clear_btn.clicked.connect(self._clear_queue)
        header_layout.addWidget(self._clear_btn)

        layout.addLayout(header_layout)

        self._queue_list = QListWidget()
        self._queue_list.setSelectionMode(QListWidget.ExtendedSelection)
        self._queue_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self._queue_list.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self._queue_list)

        action_layout = QHBoxLayout()
        self._cancel_btn = QPushButton("取消选中")
        self._cancel_btn.clicked.connect(self._cancel_selected)
        action_layout.addWidget(self._cancel_btn)

        self._promote_btn = QPushButton("提升优先级")
        self._promote_btn.clicked.connect(self._promote_selected)
        action_layout.addWidget(self._promote_btn)

        action_layout.addStretch()
        layout.addLayout(action_layout)

        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(True)
        layout.addWidget(self._progress_bar)

    def _setup_event_handlers(self):
        startup_queue.on('queue_updated', self._on_queue_updated)
        startup_queue.on('node_enqueued', self._on_node_enqueued)
        startup_queue.on('node_dequeued', self._on_node_dequeued)
        startup_queue.on('queue_empty', self._on_queue_empty)

    def _on_queue_updated(self, queue_info=None, blocked_info=None):
        self._refresh_queue_display()

    def _on_node_enqueued(self, node_name=None, **kwargs):
        self._refresh_queue_display()

    def _on_node_dequeued(self, node_name=None, **kwargs):
        self._refresh_queue_display()

    def _on_queue_empty(self):
        self._refresh_queue_display()

    def _refresh_queue_display(self):
        self._queue_list.clear()

        queue_status = startup_queue.get_queue_status()
        total = queue_status.get('total', 0)
        queued = queue_status.get('queued', 0)
        blocked = queue_status.get('blocked', 0)
        starting = queue_status.get('starting', 0)
        success = queue_status.get('success', 0)
        failed = queue_status.get('failed', 0)

        self._stats_label.setText(
            f"总计: {total} | 排队: {queued} | 阻塞: {blocked} | 启动中: {starting}"
        )

        if total > 0:
            completed = success + failed
            progress = int((completed / total) * 100)
            self._progress_bar.setValue(progress)
            self._progress_bar.setFormat(f"{completed}/{total} 完成")
        else:
            self._progress_bar.setValue(0)
            self._progress_bar.setFormat("无任务")

        queued_items = startup_queue._queue
        for i, item in enumerate(queued_items):
            list_item = QListWidgetItem()

            status_icon = ""
            status_color = QColor("gray")
            status_text = ""

            if item.status == QueueStatus.QUEUED:
                status_icon = "◎"
                status_color = QColor("#4A90E2")
                status_text = "排队中"
            elif item.status == QueueStatus.BLOCKED:
                status_icon = "⚠"
                status_color = QColor("#F5A623")
                status_text = f"阻塞中 ({', '.join(item.blocked_by)})"
            elif item.status == QueueStatus.STARTING:
                status_icon = "◐"
                status_color = QColor("#F5A623")
                status_text = "启动中..."
            elif item.status == QueueStatus.SUCCESS:
                status_icon = "✓"
                status_color = QColor("green")
                status_text = "已成功"
            elif item.status == QueueStatus.FAILED:
                status_icon = "✗"
                status_color = QColor("red")
                status_text = f"失败: {item.error_message or ''}"
            elif item.status == QueueStatus.CANCELLED:
                status_icon = "✕"
                status_color = QColor("#888")
                status_text = "已取消"

            text = f"{status_icon} {item.node_name} [{status_text}]"
            if item.dependencies:
                text += f" (依赖: {', '.join(item.dependencies)})"

            list_item.setText(text)
            list_item.setForeground(status_color)

            if item.status in (QueueStatus.SUCCESS, QueueStatus.FAILED, QueueStatus.CANCELLED):
                list_item.setFlags(list_item.flags() & ~Qt.ItemIsSelectable)

            self._queue_list.addItem(list_item)

        self._update_pause_button()

    def _update_pause_button(self):
        self._pause_btn.setChecked(startup_queue._stopped)
        self._pause_btn.setText("恢复" if startup_queue._stopped else "暂停")

    def _toggle_pause(self, checked):
        if checked:
            startup_queue.stop_queue()
        else:
            startup_queue.start_queue()

    def _clear_queue(self):
        startup_queue.clear_queue()

    def _cancel_selected(self):
        selected_items = self._queue_list.selectedItems()
        for item in selected_items:
            text = item.text()
            node_name = text.split()[1]
            startup_queue.dequeue(node_name)

    def _promote_selected(self):
        selected_items = self._queue_list.selectedItems()
        for item in selected_items:
            text = item.text()
            node_name = text.split()[1]
            startup_queue.promote_node(node_name, 100)

    def _show_context_menu(self, pos):
        item = self._queue_list.itemAt(pos)
        if not item:
            return

        text = item.text()
        node_name = text.split()[1]

        menu = QMenu(self)

        cancel_action = QAction("取消排队", self)
        cancel_action.triggered.connect(lambda: startup_queue.dequeue(node_name))
        menu.addAction(cancel_action)

        promote_action = QAction("提升优先级", self)
        promote_action.triggered.connect(lambda: startup_queue.promote_node(node_name, 100))
        menu.addAction(promote_action)

        menu.exec(self._queue_list.mapToGlobal(pos))

    def closeEvent(self, event):
        self._update_timer.stop()
        startup_queue.off('queue_updated', self._on_queue_updated)
        startup_queue.off('node_enqueued', self._on_node_enqueued)
        startup_queue.off('node_dequeued', self._on_node_dequeued)
        startup_queue.off('queue_empty', self._on_queue_empty)
        super().closeEvent(event)

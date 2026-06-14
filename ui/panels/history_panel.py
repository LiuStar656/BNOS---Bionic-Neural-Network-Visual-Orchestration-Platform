"""历史面板 - Photoshop 风格历史记录查看与跳转"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel
)

from ui.core.commands.history_manager import history_manager
from ui.core.i18n import t
from ui.core.logger import logger


class HistoryPanelWidget(QWidget):
    """历史面板内容组件（由外部 QDockWidget 包装）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # 标题栏
        header = QHBoxLayout()
        title = QLabel(t("k_view_history_panel"))
        title.setFont(QFont("", 10, QFont.Weight.Bold))
        title.setStyleSheet("color: #e0e0e0;")
        header.addWidget(title)
        header.addStretch()

        self._clear_btn = QPushButton(t("k_edit_clear_history"))
        self._clear_btn.setFixedHeight(24)
        self._clear_btn.clicked.connect(self._on_clear)
        header.addWidget(self._clear_btn)
        layout.addLayout(header)

        # 历史列表
        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._list.itemClicked.connect(self._on_item_clicked)
        self._list.setStyleSheet("""
            QListWidget {
                border: 1px solid #3c3c3c;
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #2d2d2d;
            }
            QListWidget::item:alternate {
                background-color: #222222;
            }
            QListWidget::item:hover {
                background-color: #2a2d2e;
            }
            QListWidget::item:selected {
                background-color: #094771;
                color: white;
            }
        """)
        layout.addWidget(self._list)

        # 底部信息
        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: #808080; font-size: 10px; padding: 2px 4px;")
        layout.addWidget(self._info_label)

        # 连接信号
        history_manager.history_changed.connect(self._refresh)
        history_manager.index_changed.connect(self._highlight_index)

        self._refresh()

    def _refresh(self):
        """全量刷新列表"""
        entries = history_manager.get_history_entries()
        self._list.clear()

        for entry in entries:
            item = QListWidgetItem(self._format_entry(entry))
            item.setData(Qt.ItemDataRole.UserRole, entry["index"])
            if entry["is_future"]:
                item.setForeground(Qt.GlobalColor.gray)
            self._list.addItem(item)

        # 高亮当前项
        current_idx = history_manager.get_current_index()
        if 0 <= current_idx < self._list.count():
            self._list.setCurrentRow(current_idx)
            current_item = self._list.item(current_idx)
            if current_item:
                font = QFont("", 10)
                font.setBold(True)
                current_item.setFont(font)
                current_item.setForeground(Qt.GlobalColor.yellow)

        # 更新底部信息
        total = len(entries)
        current = current_idx + 1 if current_idx >= 0 else 0
        self._info_label.setText(
            f"第 {current}/{total} 步  "
            + (t("k_edit_can_undo") if history_manager.can_undo() else t("k_edit_cannot_undo"))
        )

    def _highlight_index(self, index: int):
        """轻量高亮切换（不完全重建列表）"""
        # 取消旧高亮
        old_row = self._list.currentRow()
        if old_row >= 0 and old_row != index:
            old_item = self._list.item(old_row)
            if old_item:
                self._restore_item_style(old_item, old_row)

        if 0 <= index < self._list.count():
            self._list.setCurrentRow(index)
            new_item = self._list.item(index)
            if new_item:
                font = QFont("", 10)
                font.setBold(True)
                new_item.setFont(font)
                new_item.setForeground(Qt.GlobalColor.yellow)

        self._update_info()

    def _restore_item_style(self, item: QListWidgetItem, index: int):
        """恢复条目的默认样式"""
        font = QFont("", 10)
        item.setFont(font)
        entries = history_manager.get_history_entries()
        if index < len(entries) and entries[index].get("is_future"):
            item.setForeground(Qt.GlobalColor.gray)
        else:
            item.setForeground(Qt.GlobalColor.white)

    def _update_info(self):
        """更新底部信息文字"""
        entries_count = self._list.count()
        current_idx = history_manager.get_current_index()
        current = current_idx + 1 if current_idx >= 0 else 0
        self._info_label.setText(
            f"第 {current}/{entries_count} 步  "
            + (t("k_edit_can_undo") if history_manager.can_undo() else t("k_edit_cannot_undo"))
        )

    def _format_entry(self, entry: dict) -> str:
        """格式化历史条目的显示文本"""
        idx = entry["index"]
        desc = entry["description"]
        if entry["is_future"]:
            return f"[{idx}] {desc}  (未来)"
        return f"[{idx}] {desc}"

    def _on_item_clicked(self, item: QListWidgetItem):
        """点击历史条目 → 跳转"""
        target_index = item.data(Qt.ItemDataRole.UserRole)
        if target_index is None:
            return

        logger.debug("HistoryPanel: 点击跳转到 index=%d", target_index)
        result = history_manager.jump_to(target_index)
        if not result.success:
            logger.warning("跳转失败: %s", result.message)

    def _on_clear(self):
        """清空历史"""
        history_manager.clear_history()


class HistoryPanelDock(QDockWidget):
    """历史面板 Dock 包装"""

    closed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(t("k_view_history_panel"), parent)
        self.setObjectName("bnos_dock_history_panel")
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self._content = HistoryPanelWidget(self)
        self.setWidget(self._content)

    def closeEvent(self, event):
        self.closed.emit(self)
        super().closeEvent(event)

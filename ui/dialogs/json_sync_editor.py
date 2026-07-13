"""
JsonSyncEditor - 双向同步的 JSON 编辑器组件

封装了防抖保存和外部变化检测逻辑，可复用在节点配置、output.json、composite.json 等场景。
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.core.i18n import t
from ui.core.logger import logger


class JsonSyncEditor(QWidget):
    """双向同步的 JSON 编辑器组件"""

    content_changed = Signal(str)

    def __init__(self, file_path: str | Path = "", parent=None):
        super().__init__(parent)
        self._file_path = Path(file_path) if file_path else None
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._write_to_file)
        self._last_content = ""
        self._ignore_external = False
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1500)
        self._refresh_timer.timeout.connect(self._check_external_change)

        self._init_ui()
        if self._file_path:
            self.load_file()
            self._refresh_timer.start()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        tool_row = QHBoxLayout()
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: rgba(255,255,255,120); font-size: 10px; background: transparent;")
        tool_row.addWidget(self._status_label)

        refresh_btn = QPushButton(t("k_action_refresh"))
        refresh_btn.setStyleSheet(
            "background-color: #555555; color: white; padding: 3px 10px; font-size: 10px;"
            "border: none; border-radius: 3px;"
        )
        refresh_btn.clicked.connect(self.refresh)
        tool_row.addWidget(refresh_btn)
        tool_row.addStretch()

        layout.addLayout(tool_row)

        self._editor = QTextEdit()
        self._editor.setFont(QFont("Consolas", 10))
        self._editor.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                selection-background-color: #264f78;
            }
        """)
        self._editor.textChanged.connect(self._on_user_edit)
        layout.addWidget(self._editor, 1)

    def set_file_path(self, file_path: str | Path):
        """设置要编辑的文件路径"""
        self._file_path = Path(file_path) if file_path else None
        if self._file_path:
            self.load_file()
            self._refresh_timer.start()
        else:
            self._refresh_timer.stop()
            self._editor.setPlainText("# No file selected")

    def load_file(self):
        """从文件加载内容到编辑器"""
        if not self._file_path:
            return

        if not self._file_path.exists():
            self._editor.setPlainText("")
            self._last_content = ""
            return

        try:
            raw = self._file_path.read_text(encoding="utf-8")
            if not raw.strip():
                display = ""
                self._last_content = ""
            else:
                try:
                    data = json.loads(raw)
                    display = json.dumps(data, indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    display = raw
                self._last_content = display

            self._editor.blockSignals(True)
            self._editor.setPlainText(display)
            self._editor.blockSignals(False)
        except Exception as e:
            logger.error(f"JsonSyncEditor load_file error: {e}")
            self._last_content = ""

    def _on_user_edit(self):
        """用户编辑文本 → 启动防抖保存定时器"""
        self._save_timer.start(800)

    def _write_to_file(self):
        """将编辑器内容写入文件，同步更新编辑器显示"""
        if not self._file_path or self._ignore_external:
            return

        content = self._editor.toPlainText()
        if content.startswith("#"):
            return
        if content == self._last_content:
            return

        try:
            try:
                data = json.loads(content)
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                formatted = content

            self._last_content = formatted
            self._ignore_external = True

            self._file_path.parent.mkdir(parents=True, exist_ok=True)
            self._file_path.write_text(formatted, encoding="utf-8")

            self._editor.blockSignals(True)
            self._editor.setPlainText(formatted)
            self._editor.blockSignals(False)

            self._set_status(t("k_status_saved"), "#4CAF50")
            self.content_changed.emit(formatted)

            QTimer.singleShot(500, self._reset_ignore_flag)
        except Exception as e:
            self._set_status(t("k_status_save_failed"), "#F44336")
            logger.error(f"JsonSyncEditor write_to_file error: {e}")

    def _reset_ignore_flag(self):
        self._ignore_external = False

    def _check_external_change(self):
        """检测文件是否存在外部变更"""
        if self._ignore_external or not self._file_path or not self._file_path.exists():
            return

        try:
            file_content = self._file_path.read_text(encoding="utf-8")
            if not file_content.strip():
                file_display = ""
            else:
                try:
                    data = json.loads(file_content)
                    file_display = json.dumps(data, indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    file_display = file_content
        except Exception:
            return

        if file_display == self._last_content:
            return

        editor_content = self._editor.toPlainText()
        if self._same_json(file_display, editor_content):
            return

        self.load_file()
        self._set_status(t("k_status_updated"), "#2196F3")

    @staticmethod
    def _same_json(a: str, b: str) -> bool:
        """比较两个 JSON 字符串是否语义等价"""
        if a == b:
            return True
        try:
            da = json.loads(a)
            db = json.loads(b)
            return da == db
        except json.JSONDecodeError:
            return False

    def refresh(self):
        """手动刷新：强制从文件重新加载"""
        self._save_timer.stop()
        self.load_file()
        self._set_status(t("k_status_refreshed"), "#2196F3")

    def _set_status(self, text: str, color: str):
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color}; font-size: 10px; background: transparent;")

    def close(self):
        """关闭前停止定时器并保存编辑"""
        self._refresh_timer.stop()
        self._save_timer.stop()
        self._write_to_file()
        super().close()

    def get_content(self) -> str:
        """获取当前编辑器内容"""
        return self._editor.toPlainText()

    def set_content(self, content: str):
        """设置编辑器内容（不触发保存）"""
        self._editor.blockSignals(True)
        self._editor.setPlainText(content)
        self._editor.blockSignals(False)
        self._last_content = content

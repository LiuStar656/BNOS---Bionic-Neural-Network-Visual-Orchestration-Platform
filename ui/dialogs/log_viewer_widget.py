"""
LogViewerWidget - 日志查看器组件

封装了日志文件选择、轮询更新和清除功能，可复用在普通节点和复合节点的日志查看场景。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.core.i18n import t
from ui.core.utils.dialog_utils import themed_message


class LogViewerWidget(QWidget):
    """日志查看器组件"""

    def __init__(self, log_dir: str | Path = "", parent=None):
        super().__init__(parent)
        self._log_dir = Path(log_dir) if log_dir else None
        self._current_log_file = ""
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1500)
        self._refresh_timer.timeout.connect(self._check_log_change)

        self._init_ui()
        if self._log_dir:
            self.load_log_files()
            self._refresh_timer.start()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        log_file_layout = QHBoxLayout()
        log_file_label = QLabel(t("k_log_file_label"))
        log_file_layout.addWidget(log_file_label)

        self.log_file_combo = QComboBox()
        self.log_file_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                padding: 3px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.log_file_combo.currentIndexChanged.connect(self.on_log_file_changed)
        log_file_layout.addWidget(self.log_file_combo)
        log_file_layout.addStretch()

        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.setStyleSheet("background-color: #666666; color: white; padding: 5px 15px;")
        self.clear_log_btn.clicked.connect(self.clear_current_log)
        log_file_layout.addWidget(self.clear_log_btn)

        layout.addLayout(log_file_layout)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                selection-background-color: #264f78;
            }
        """)
        layout.addWidget(self.output_text, 1)

    def set_log_dir(self, log_dir: str | Path):
        """设置日志目录"""
        self._log_dir = Path(log_dir) if log_dir else None
        if self._log_dir:
            self.load_log_files()
            self._refresh_timer.start()
        else:
            self._refresh_timer.stop()
            self.output_text.setPlainText("# No log directory")

    def load_log_files(self):
        """加载所有 .log 文件"""
        if not self._log_dir or not self._log_dir.exists():
            self.output_text.setPlainText(
                "# logs directory does not exist\n# Tip: the log directory and files are created automatically when the node starts"
            )
            self._current_log_file = ""
            self.log_file_combo.blockSignals(True)
            self.log_file_combo.clear()
            self.log_file_combo.blockSignals(False)
            return

        try:
            log_files = sorted([f.name for f in self._log_dir.iterdir() if f.is_file() and f.name.endswith(".log")])
            self.log_file_combo.blockSignals(True)
            old_current = self.log_file_combo.currentText() if self.log_file_combo.count() > 0 else ""
            self.log_file_combo.clear()
            for log_file in log_files:
                self.log_file_combo.addItem(log_file)
            if old_current and old_current in log_files:
                idx = log_files.index(old_current)
                self.log_file_combo.setCurrentIndex(idx)
            elif log_files:
                self.log_file_combo.setCurrentIndex(0)
            self.log_file_combo.blockSignals(False)

            if log_files:
                self._current_log_file = self.log_file_combo.currentText()
                self._load_log_content(self._current_log_file)
        except OSError:
            pass

    def _load_log_content(self, log_filename: str):
        """加载日志文件内容"""
        log_path = self._log_dir / log_filename
        try:
            if not log_path.exists():
                self.output_text.setPlainText(f"# Log file not found: {log_filename}")
                return

            content = log_path.read_text(encoding="utf-8", errors="replace")
            if not content.strip():
                self.output_text.setPlainText(t("k_log_empty"))
            else:
                self.output_text.setPlainText(content)
            scrollbar = self.output_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except (AttributeError, RuntimeError):
            pass

    def on_log_file_changed(self, index: int):
        """切换日志文件"""
        if index >= 0:
            log_filename = self.log_file_combo.itemText(index)
            self._current_log_file = log_filename
            self._load_log_content(log_filename)

    def _check_log_change(self):
        """检测日志文件是否有变化"""
        if not self._current_log_file or not self._log_dir:
            return
        log_path = self._log_dir / self._current_log_file
        if not log_path.exists():
            return
        try:
            content = log_path.read_text(encoding="utf-8", errors="replace")
            if content != self.output_text.toPlainText():
                self.output_text.setPlainText(content)
                scrollbar = self.output_text.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
        except Exception:
            pass

    def clear_current_log(self):
        """清除当前日志文件"""
        if self.log_file_combo.count() == 0:
            themed_message(self, t("k_title_warning"), t("k_log_no_clear"), "warning")
            return

        log_filename = self.log_file_combo.currentText()
        log_path = self._log_dir / log_filename

        reply = themed_message(
            self, t("k_title_confirm_clear"), t("_k_clear_log_file_confirm").format(name=log_filename), "question"
        )

        if reply:
            try:
                log_path.write_text("", encoding="utf-8")
                self.output_text.setPlainText(t("k_log_cleared"))
            except Exception as e:
                themed_message(self, t("k_title_error"), t("_k_log_file_clear_fail").format(err=str(e)), "error")

    def close(self):
        """关闭前停止定时器"""
        self._refresh_timer.stop()
        super().close()

    def refresh(self):
        """手动刷新日志内容"""
        if self._current_log_file:
            self._load_log_content(self._current_log_file)

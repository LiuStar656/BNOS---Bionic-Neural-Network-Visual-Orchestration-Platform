"""
节点展开面板 - 浮动在画布节点旁的半透明悬浮窗
参照 NodeListPanel 样式：无边框、半透明深色背景、可拖动
展开坐标以节点在画布上的位置为基准
output.json 编辑区：始终可编辑，输入自动保存到文件，外部变化自动刷新
"""
import os
import json
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QMessageBox,
)
from ui.core.utils.dialog_utils import themed_message
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from ui.core.floating_panel import FloatingPanel
from ui.core.i18n import t
from ui.core.logger import logger
from ui.core.polling_manager import polling_manager


class NodeExpandPanel(FloatingPanel):
    """节点展开面板 - output.json 双向实时同步编辑"""

    def __init__(self, node_name, parent_window=None):
        super().__init__(parent_window, title=t("k_info_details_title"))
        self.node_name = node_name
        self._save_timer = None      # 防抖保存定时器
        self._last_content = ""      # 上次写入文件的内容（阻止回环刷新）
        self._ignore_external = False  # 正在自行保存时忽略外部变化
        self._output_path = ""

        # 获取节点数据
        self._node_info = None
        self._node_path = None
        if parent_window and node_name in parent_window.nodes_data:
            self._node_info = parent_window.nodes_data[node_name]
            self._node_path = self._node_info.get('path', '')

        if self._node_path:
            self._output_path = os.path.join(self._node_path, "output.json")

        self.resize(620, 380)
        self.setMinimumSize(480, 300)
        self._init_ui()
        self._load_output_json()

        # 自动刷新定时器（每 1.5 秒检测外部文件变化）
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._refresh_timer.timeout.connect(self._check_external_change)
        self._refresh_timer.start(1500)

        # 防抖保存定时器（用户停止输入 800ms 后自动保存）
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._write_to_file)

    def _init_ui(self):
        """初始化UI — 使用基类 content_layout"""
        main_h_layout = QHBoxLayout()
        main_h_layout.setSpacing(8)

        # ===== 左侧：output.json 编辑区 =====
        left_layout = QVBoxLayout()

        # 工具栏：状态指示 + 手动刷新
        tool_row = QHBoxLayout()

        self._status_indicator = QLabel(t("k_action_live"))
        self._status_indicator.setStyleSheet(
            "color: #4CAF50; font-size: 10px; padding: 2px 5px;"
        )
        tool_row.addWidget(self._status_indicator)

        refresh_btn = QPushButton(t("k_action_refresh"))
        refresh_btn.setStyleSheet(
            "background-color: #555555; color: white; padding: 3px 10px; font-size: 10px;"
            "border: none; border-radius: 3px;"
        )
        refresh_btn.clicked.connect(self._on_manual_refresh)
        tool_row.addWidget(refresh_btn)
        tool_row.addStretch()
        left_layout.addLayout(tool_row)

        # JSON 编辑器（始终可编辑，直接对接文件）
        self._output_editor = QTextEdit()
        self._output_editor.setFont(QFont("Consolas", 9))
        self._output_editor.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 3px;
                selection-background-color: #264f78;
            }
        """)
        self._output_editor.textChanged.connect(self._on_user_edit)
        left_layout.addWidget(self._output_editor, 1)

        main_h_layout.addLayout(left_layout, 3)

        # ===== 右侧：信息 + 操作按钮 =====
        right_layout = QVBoxLayout()
        right_layout.setSpacing(6)

        # 节点信息
        info_group = QGroupBox(t("k_info_details"))
        info_group.setStyleSheet("""
            QGroupBox {
                color: rgba(255, 255, 255, 180);
                font-size: 10px;
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
        """)
        info_layout = QVBoxLayout(info_group)
        name_label = QLabel(str(self.node_name))
        name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        name_label.setStyleSheet("color: white;")
        info_layout.addWidget(name_label)

        status = self._node_info.get('status', 'stopped') if self._node_info else 'stopped'
        status_text = t("k_status_running") if status == 'running' else t("k_status_stopped")
        status_color = "#4CAF50" if status == 'running' else "#999"
        self._status_label = QLabel(status_text)
        self._status_label.setStyleSheet(f"color: {status_color}; font-size: 10px;")
        info_layout.addWidget(self._status_label)
        right_layout.addWidget(info_group)

        # 操作按钮组
        action_group = QGroupBox(t("k_info_actions"))
        action_group.setStyleSheet("""
            QGroupBox {
                color: rgba(255, 255, 255, 180);
                font-size: 10px;
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }
        """)
        action_layout = QVBoxLayout(action_group)
        action_layout.setSpacing(4)

        btn_style = (
            "color: white; padding: 6px; font-weight: bold; font-size: 11px;"
            "border: none; border-radius: 3px;"
        )

        # 启动
        self._start_btn = QPushButton(t("k_node_start"))
        self._start_btn.setStyleSheet(f"background-color: #333333; {btn_style}")
        self._start_btn.clicked.connect(self._start_node)
        action_layout.addWidget(self._start_btn)

        # 停止
        self._stop_btn = QPushButton(t("k_node_stop"))
        self._stop_btn.setStyleSheet(f"background-color: #555555; {btn_style}")
        self._stop_btn.clicked.connect(self._stop_node)
        action_layout.addWidget(self._stop_btn)

        # 根据当前状态调整
        if status == 'running':
            self._start_btn.setEnabled(False)
            self._start_btn.setStyleSheet(f"background-color: #3a3a3a; color: #888; {btn_style}")
        else:
            self._stop_btn.setEnabled(False)
            self._stop_btn.setStyleSheet(f"background-color: #3a3a3a; color: #888; {btn_style}")

        # 节点配置
        config_btn = QPushButton(t("k_node_config"))
        config_btn.setStyleSheet(f"background-color: #555555; {btn_style}")
        config_btn.clicked.connect(self._open_config)
        action_layout.addWidget(config_btn)

        # 删除节点
        delete_btn = QPushButton(t("k_node_delete"))
        delete_btn.setStyleSheet(f"background-color: #666666; {btn_style}")
        delete_btn.clicked.connect(self._delete_node)
        action_layout.addWidget(delete_btn)

        right_layout.addWidget(action_group)
        right_layout.addStretch()

        main_h_layout.addLayout(right_layout, 1)

        self.content_layout.addLayout(main_h_layout)

    # ==================== output.json 双向同步 ====================

    def _load_output_json(self):
        """从文件加载内容到编辑器（不触发 textChanged 保存）"""
        if not self._output_path:
            self._output_editor.setPlainText("# 节点路径无效")
            self._last_content = ""
            return

        if not os.path.exists(self._output_path):
            self._output_editor.setPlainText("")
            self._last_content = ""
            return

        try:
            with open(self._output_path, 'r', encoding='utf-8') as f:
                raw = f.read()

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
        except Exception as e:
            display = f"# 读取失败: {e}"
            self._last_content = ""

        # 阻止 textChanged 触发保存
        self._output_editor.blockSignals(True)
        self._output_editor.setPlainText(display)
        self._output_editor.blockSignals(False)

    def _on_user_edit(self):
        """用户编辑文本 → 启动防抖保存定时器"""
        self._save_timer.start(800)

    def _write_to_file(self):
        """将编辑器内容写入 output.json 文件，同步更新编辑器显示"""
        if not self._output_path or self._ignore_external:
            return

        content = self._output_editor.toPlainText()

        # 跳过占位提示文本（以 # 开头）
        if content.startswith("#"):
            return

        # 若内容与上次写入一致，跳过
        if content == self._last_content:
            return

        try:
            # 尝试格式化 JSON
            try:
                data = json.loads(content)
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                formatted = content

            self._last_content = formatted
            self._ignore_external = True

            with open(self._output_path, 'w', encoding='utf-8') as f:
                f.write(formatted)

            # 编辑器同步为格式化后的内容（阻止回环保存）
            self._output_editor.blockSignals(True)
            self._output_editor.setPlainText(formatted)
            self._output_editor.blockSignals(False)

            self._set_status(t("k_status_saved"), "#4CAF50")
            logger.debug("output.json 已保存: %s", self._output_path)

        except Exception as e:
            self._set_status(t("k_status_save_failed"), "#F44336")
            logger.error("保存 output.json 失败: %s", e)
        finally:
            QTimer.singleShot(500, self._reset_ignore_flag)

    def _reset_ignore_flag(self):
        self._ignore_external = False

    def _check_external_change(self):
        """检测文件是否存在外部变更，有则刷新编辑器"""
        if self._ignore_external or not self._output_path:
            return

        if not os.path.exists(self._output_path):
            return

        try:
            with open(self._output_path, 'r', encoding='utf-8') as f:
                file_content = f.read()

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

        # 文件内容跟上次写入一致 → 是自己保存的，跳过
        if file_display == self._last_content:
            return

        editor_content = self._output_editor.toPlainText()

        # 字符串不同但语义相同（仅格式差异）→ 跳过，不刷新
        if self._same_json(file_display, editor_content):
            return

        # 真正的外部修改 → 刷新编辑器
        self._load_output_json()
        self._set_status(t("k_status_updated"), "#2196F3")

    @staticmethod
    def _same_json(a, b):
        """比较两个 JSON 字符串是否语义等价（忽略格式差异）"""
        if a == b:
            return True
        try:
            da = json.loads(a)
            db = json.loads(b)
            return da == db
        except json.JSONDecodeError:
            return False

    def _on_manual_refresh(self):
        """手动刷新：强制从文件重新加载"""
        self._save_timer.stop()  # 取消待处理的保存
        self._load_output_json()
        self._set_status(t("k_status_refreshed"), "#2196F3")

    def _set_status(self, text, color):
        self._status_indicator.setText(text)
        self._status_indicator.setStyleSheet(
            f"color: {color}; font-size: 10px; padding: 2px 5px;"
        )

    def _start_node(self):
        """启动节点"""
        if self.parent_window:
            self.parent_window.start_selected_node_by_name(self.node_name)
            self._refresh_status()

    def _stop_node(self):
        """停止节点"""
        if self.parent_window:
            self.parent_window.stop_selected_node_by_name(self.node_name)
            self._refresh_status()

    def _refresh_status(self):
        """刷新按钮和状态显示"""
        if self.parent_window and self.node_name in self.parent_window.nodes_data:
            self._node_info = self.parent_window.nodes_data[self.node_name]
            status = self._node_info.get('status', 'stopped')
            is_running = status == 'running'

            self._status_label.setText(t("k_status_running") if is_running else t("k_status_stopped"))
            self._status_label.setStyleSheet(
                f"color: {'#4CAF50' if is_running else '#999'}; font-size: 10px;"
            )

            self._start_btn.setEnabled(not is_running)
            self._stop_btn.setEnabled(is_running)
            btn_style = (
                "color: white; padding: 6px; font-weight: bold; font-size: 11px;"
                "border: none; border-radius: 3px;"
            )
            disabled_style = (
                "background-color: #3a3a3a; color: #888; padding: 6px; "
                "font-weight: bold; font-size: 11px; border: none; border-radius: 3px;"
            )
            if is_running:
                self._start_btn.setStyleSheet(disabled_style)
                self._stop_btn.setStyleSheet(f"background-color: #555555; {btn_style}")
            else:
                self._start_btn.setStyleSheet(f"background-color: #333333; {btn_style}")
                self._stop_btn.setStyleSheet(disabled_style)

    def _open_config(self):
        """打开节点配置对话框"""
        if self.parent_window and self.node_name in self.parent_window.nodes_data:
            node_info = self.parent_window.nodes_data[self.node_name]
            from ui.panels.property_panel import NodeConfigDialog
            dialog = NodeConfigDialog(
                self.node_name,
                node_info.get('config', {}),
                node_info.get('path', ''),
                self.parent_window
            )
            dialog.exec()

    def _delete_node(self):
        """从画布删除节点"""
        reply = themed_message(self, t("k_title_confirm_delete"), t("_k_node_expand_confirm_delete").format(name=self.node_name),
            "question")
        if not reply:
            return
        if self.parent_window and hasattr(self.parent_window, 'canvas'):
            self.parent_window.canvas.remove_node_with_cleanup(self.node_name)
        self._close()

    def _close(self):
        """关闭面板前停止定时器并保存编辑"""
        self._refresh_timer.stop()
        self._save_timer.stop()
        # 确保最终写入
        self._write_to_file()
        self.close()

    # ==================== 鼠标拖动支持（与 NodeListPanel 一致）====================

    def mousePressEvent(self, event):
        """鼠标按下 — 开始拖动"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动 — 拖动窗口"""
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    # ==================== 生命周期 ====================

    def closeEvent(self, event):
        """关闭时停止定时器并最终保存"""
        self._refresh_timer.stop()
        self._save_timer.stop()
        self._write_to_file()
        super().closeEvent(event)
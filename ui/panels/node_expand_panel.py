"""
节点展开面板 - 浮动在画布节点旁的半透明悬浮窗
参照 NodeListPanel 样式：无边框、半透明深色背景、可拖动
展开坐标以节点在画布上的位置为基准
"""
import os
import json
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from ui.core.floating_panel import FloatingPanel


class NodeExpandPanel(FloatingPanel):
    """节点展开面板（浮动半透明悬浮窗，在节点旁展开）"""

    def __init__(self, node_name, parent_window=None):
        super().__init__(parent_window, title="节点详情")
        self.node_name = node_name
        self._output_editable = False
        self._last_mtime = 0
        self._auto_refresh = True

        # 获取节点数据
        self._node_info = None
        self._node_path = None
        if parent_window and node_name in parent_window.nodes_data:
            self._node_info = parent_window.nodes_data[node_name]
            self._node_path = self._node_info.get('path', '')

        self.resize(620, 380)
        self.setMinimumSize(480, 300)
        self._init_ui()
        self._load_output_json()

        # 自动刷新定时器（每 2 秒检测 output.json 变化）
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._refresh_timer.timeout.connect(self._auto_refresh_output)
        self._refresh_timer.start(2000)

    def _init_ui(self):
        """初始化UI — 使用基类 content_layout"""
        main_h_layout = QHBoxLayout()
        main_h_layout.setSpacing(8)

        # ===== 左侧：output.json 编辑区 =====
        left_layout = QVBoxLayout()

        # 工具栏：锁定 + 刷新
        tool_row = QHBoxLayout()
        self._toggle_btn = QPushButton("解锁编辑")
        self._toggle_btn.setStyleSheet(
            "background-color: #555555; color: white; padding: 3px 10px; font-size: 10px;"
            "border: none; border-radius: 3px;"
        )
        self._toggle_btn.clicked.connect(self._toggle_editable)
        tool_row.addWidget(self._toggle_btn)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(
            "background-color: #555555; color: white; padding: 3px 10px; font-size: 10px;"
            "border: none; border-radius: 3px;"
        )
        refresh_btn.clicked.connect(self._load_output_json)
        tool_row.addWidget(refresh_btn)

        # 实时刷新状态指示
        self._live_indicator = QLabel("实时")
        self._live_indicator.setStyleSheet(
            "color: #4CAF50; font-size: 10px; padding: 2px 5px;"
        )
        tool_row.addWidget(self._live_indicator)
        tool_row.addStretch()
        left_layout.addLayout(tool_row)

        # JSON 编辑器（深色主题）
        self._output_editor = QTextEdit()
        self._output_editor.setReadOnly(True)
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
        left_layout.addWidget(self._output_editor, 1)

        main_h_layout.addLayout(left_layout, 3)

        # ===== 右侧：信息 + 操作按钮 =====
        right_layout = QVBoxLayout()
        right_layout.setSpacing(6)

        # 节点信息
        info_group = QGroupBox("信息")
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
        status_text = "运行中" if status == 'running' else "已停止"
        status_color = "#4CAF50" if status == 'running' else "#999"
        self._status_label = QLabel(status_text)
        self._status_label.setStyleSheet(f"color: {status_color}; font-size: 10px;")
        info_layout.addWidget(self._status_label)
        right_layout.addWidget(info_group)

        # 操作按钮组
        action_group = QGroupBox("操作")
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
        self._start_btn = QPushButton("启动节点")
        self._start_btn.setStyleSheet(f"background-color: #333333; {btn_style}")
        self._start_btn.clicked.connect(self._start_node)
        action_layout.addWidget(self._start_btn)

        # 停止
        self._stop_btn = QPushButton("停止节点")
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
        config_btn = QPushButton("节点配置")
        config_btn.setStyleSheet(f"background-color: #555555; {btn_style}")
        config_btn.clicked.connect(self._open_config)
        action_layout.addWidget(config_btn)

        # 删除节点
        delete_btn = QPushButton("删除节点")
        delete_btn.setStyleSheet(f"background-color: #666666; {btn_style}")
        delete_btn.clicked.connect(self._delete_node)
        action_layout.addWidget(delete_btn)

        right_layout.addWidget(action_group)
        right_layout.addStretch()

        main_h_layout.addLayout(right_layout, 1)

        self.content_layout.addLayout(main_h_layout)

    # ==================== 功能方法 ====================

    def _load_output_json(self):
        """加载 output.json 文件内容"""
        if not self._node_path:
            self._output_editor.setPlainText("# 节点路径无效")
            self._last_mtime = 0
            return

        output_path = os.path.join(self._node_path, "output.json")
        if not os.path.exists(output_path):
            self._output_editor.setPlainText("# output.json 不存在\n# 节点运行后将自动生成")
            self._last_mtime = 0
            return

        # 记录文件当前修改时间
        self._last_mtime = os.path.getmtime(output_path)

        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if not content:
                self._output_editor.setPlainText("# output.json 为空")
            else:
                try:
                    data = json.loads(content)
                    self._output_editor.setPlainText(
                        json.dumps(data, indent=2, ensure_ascii=False)
                    )
                except json.JSONDecodeError:
                    self._output_editor.setPlainText(content)
        except Exception as e:
            self._output_editor.setPlainText(f"# 读取失败: {e}")

    def _auto_refresh_output(self):
        """定时检测 output.json 是否变化，变化且非编辑模式时自动刷新"""
        if not self._auto_refresh or not self._node_path:
            return

        output_path = os.path.join(self._node_path, "output.json")
        if not os.path.exists(output_path):
            return

        try:
            current_mtime = os.path.getmtime(output_path)
        except OSError:
            return

        if current_mtime > self._last_mtime:
            # 文件有更新，自动重新加载
            self._load_output_json()

    def _toggle_editable(self):
        """切换编辑/只读状态（编辑模式暂停自动刷新）"""
        self._output_editable = not self._output_editable
        self._output_editor.setReadOnly(not self._output_editable)
        self._toggle_btn.setText("锁定编辑" if self._output_editable else "解锁编辑")
        self._toggle_btn.setStyleSheet(
            f"background-color: {'#333333' if self._output_editable else '#555555'}; "
            "color: white; padding: 3px 10px; font-size: 10px; "
            "border: none; border-radius: 3px;"
        )
        # 编辑模式下暂停自动刷新，只读模式下恢复
        self._auto_refresh = not self._output_editable
        self._live_indicator.setText("编辑" if self._output_editable else "实时")
        self._live_indicator.setStyleSheet(
            f"color: {'#FF9800' if self._output_editable else '#4CAF50'}; "
            "font-size: 10px; padding: 2px 5px;"
        )

    def _save_output_json(self):
        """保存 output.json"""
        if not self._output_editable or not self._node_path:
            return
        output_path = os.path.join(self._node_path, "output.json")
        content = self._output_editor.toPlainText().strip()
        try:
            try:
                data = json.loads(content)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

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

            self._status_label.setText("运行中" if is_running else "已停止")
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
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要从画布中删除节点 '{self.node_name}' 吗？\n\n"
            f"这将从画布视图中移除该节点及所有相关连线，\n"
            f"不会删除节点文件夹和配置文件。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if self.parent_window and hasattr(self.parent_window, 'canvas'):
            self.parent_window.canvas.remove_node_with_cleanup(self.node_name)
        self._close()

    def _close(self):
        """关闭面板前停止定时器并保存编辑"""
        self._refresh_timer.stop()
        self._save_output_json()
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
        """关闭时停止定时器并保存"""
        self._refresh_timer.stop()
        self._save_output_json()
        super().closeEvent(event)

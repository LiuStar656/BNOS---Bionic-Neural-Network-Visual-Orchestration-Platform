"""
调试面板 - 节点调试和日志查看工具

功能特性：
- 调试会话管理
- 日志断点设置
- 实时变量查看
- 节点日志显示
- 调试控制（启动/暂停/恢复/停止）
"""
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QLineEdit, QComboBox,
    QCheckBox, QSplitter
)
from PySide6.QtCore import Qt, QTimer, Signal
from ui.core.floating_panel import FloatingPanel
from ui.core.i18n import t
from ui.core.logger import logger
from ui.core.node_debugger import node_debugger, DebugMode


class DebugPanel(FloatingPanel):
    """调试面板"""

    def __init__(self, parent=None):
        super().__init__(parent, title=t("k_debug"))
        self._selected_node = None
        self._log_buffer = []
        
        self.resize(800, 600)
        self.setMinimumSize(600, 400)
        
        self._init_ui()
        self._start_polling()
        
        node_debugger.subscribe('debug.start', self._on_debug_start)
        node_debugger.subscribe('debug.stop', self._on_debug_stop)
        node_debugger.subscribe('debug.pause', self._on_debug_pause)
        node_debugger.subscribe('debug.resume', self._on_debug_resume)

    def _init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        splitter = QSplitter(Qt.Vertical)

        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        left_group = QGroupBox(t("k_sessions"))
        left_layout = QVBoxLayout(left_group)
        left_layout.setContentsMargins(8, 4, 8, 8)

        self._session_table = QTableWidget()
        self._session_table.setColumnCount(4)
        self._session_table.setHorizontalHeaderLabels([
            t("k_node_name"), t("k_status"), t("k_port"), t("k_mode")
        ])
        self._session_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._session_table.verticalHeader().setVisible(False)
        self._session_table.setStyleSheet("""
            QTableWidget { background-color: #1a1a1a; color: #b0b0b0; font-size: 11px; }
            QHeaderView::section { background-color: #2d2d30; color: #d4d4d4; font-size: 10px; }
        """)
        self._session_table.cellClicked.connect(self._on_session_selected)
        left_layout.addWidget(self._session_table)

        control_layout = QHBoxLayout()
        self._start_btn = QPushButton(t("k_start"))
        self._start_btn.clicked.connect(self._start_debug)
        self._stop_btn = QPushButton(t("k_stop"))
        self._stop_btn.clicked.connect(self._stop_debug)
        self._pause_btn = QPushButton(t("k_pause"))
        self._pause_btn.clicked.connect(self._pause_debug)
        self._resume_btn = QPushButton(t("k_resume"))
        self._resume_btn.clicked.connect(self._resume_debug)
        
        control_layout.addWidget(self._start_btn)
        control_layout.addWidget(self._stop_btn)
        control_layout.addWidget(self._pause_btn)
        control_layout.addWidget(self._resume_btn)
        left_layout.addLayout(control_layout)

        top_layout.addWidget(left_group)

        right_group = QGroupBox(t("k_breakpoints"))
        right_layout = QVBoxLayout(right_group)
        right_layout.setContentsMargins(8, 4, 8, 8)

        bp_input_layout = QHBoxLayout()
        self._bp_pattern = QLineEdit()
        self._bp_pattern.setPlaceholderText(t("k_log_pattern"))
        self._bp_action = QComboBox()
        self._bp_action.addItems([t("k_pause"), t("k_log"), t("k_alert")])
        self._add_bp_btn = QPushButton(t("k_add"))
        self._add_bp_btn.clicked.connect(self._add_breakpoint)
        
        bp_input_layout.addWidget(self._bp_pattern)
        bp_input_layout.addWidget(self._bp_action)
        bp_input_layout.addWidget(self._add_bp_btn)
        right_layout.addLayout(bp_input_layout)

        self._bp_table = QTableWidget()
        self._bp_table.setColumnCount(3)
        self._bp_table.setHorizontalHeaderLabels([
            t("k_pattern"), t("k_action"), t("k_hits")
        ])
        self._bp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._bp_table.verticalHeader().setVisible(False)
        self._bp_table.setStyleSheet("""
            QTableWidget { background-color: #1a1a1a; color: #b0b0b0; font-size: 11px; }
            QHeaderView::section { background-color: #2d2d30; color: #d4d4d4; font-size: 10px; }
        """)
        right_layout.addWidget(self._bp_table)

        clear_bp_btn = QPushButton(t("k_clear_all"))
        clear_bp_btn.clicked.connect(self._clear_breakpoints)
        right_layout.addWidget(clear_bp_btn)

        top_layout.addWidget(right_group)

        splitter.addWidget(top_widget)

        bottom_tab = QSplitter(Qt.Horizontal)

        log_group = QGroupBox(t("k_logs"))
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(8, 4, 8, 8)

        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setStyleSheet("""
            QTextEdit { background-color: #1e1e1e; color: #b0b0b0; font-size: 11px; font-family: Consolas; }
        """)
        log_layout.addWidget(self._log_edit)

        auto_scroll = QCheckBox(t("k_auto_scroll"))
        auto_scroll.setChecked(True)
        self._auto_scroll = auto_scroll
        log_layout.addWidget(auto_scroll)

        bottom_tab.addWidget(log_group)

        vars_group = QGroupBox(t("k_variables"))
        vars_layout = QVBoxLayout(vars_group)
        vars_layout.setContentsMargins(8, 4, 8, 8)

        self._vars_table = QTableWidget()
        self._vars_table.setColumnCount(2)
        self._vars_table.setHorizontalHeaderLabels([t("k_name"), t("k_value")])
        self._vars_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._vars_table.verticalHeader().setVisible(False)
        self._vars_table.setStyleSheet("""
            QTableWidget { background-color: #1a1a1a; color: #b0b0b0; font-size: 11px; }
            QHeaderView::section { background-color: #2d2d30; color: #d4d4d4; font-size: 10px; }
        """)
        vars_layout.addWidget(self._vars_table)

        refresh_vars_btn = QPushButton(t("k_refresh"))
        refresh_vars_btn.clicked.connect(self._refresh_variables)
        vars_layout.addWidget(refresh_vars_btn)

        bottom_tab.addWidget(vars_group)

        splitter.addWidget(bottom_tab)

        splitter.setSizes([250, 350])
        main_layout.addWidget(splitter)

        self.content_layout.addLayout(main_layout)

    def _start_polling(self):
        """开始轮询更新"""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)
        self._timer.start(1000)

    def _update(self):
        """更新面板内容"""
        self._update_sessions()
        self._update_logs()
        self._update_variables()

    def _update_sessions(self):
        """更新会话列表"""
        sessions = node_debugger.get_active_sessions()
        
        self._session_table.setRowCount(len(sessions))
        for i, session in enumerate(sessions):
            self._session_table.setItem(i, 0, QTableWidgetItem(session['node_name']))
            self._session_table.setItem(i, 1, QTableWidgetItem(session['state']))
            self._session_table.setItem(i, 2, QTableWidgetItem(str(session['port'])))
            self._session_table.setItem(i, 3, QTableWidgetItem(session['mode']))

    def _update_logs(self):
        """更新日志显示"""
        if not self._selected_node:
            return

        logs = node_debugger.get_logs(self._selected_node)
        if logs:
            self._log_edit.append("\n".join(logs[-50:]))
            if self._auto_scroll.isChecked():
                self._log_edit.verticalScrollBar().setValue(
                    self._log_edit.verticalScrollBar().maximum()
                )

    def _update_variables(self):
        """更新变量显示"""
        if not self._selected_node:
            return

        variables = node_debugger.get_variables(self._selected_node)
        
        self._vars_table.setRowCount(len(variables))
        for i, (name, value) in enumerate(variables.items()):
            self._vars_table.setItem(i, 0, QTableWidgetItem(name))
            self._vars_table.setItem(i, 1, QTableWidgetItem(str(value)))

    def _on_session_selected(self, row, column):
        """会话选择变化"""
        item = self._session_table.item(row, 0)
        if item:
            self._selected_node = item.text()

    def _start_debug(self):
        """启动调试"""
        if not self._selected_node:
            return

        node_debugger.start_debug(self._selected_node, "", DebugMode.DEBUGPY)

    def _stop_debug(self):
        """停止调试"""
        if not self._selected_node:
            return

        node_debugger.stop_debug(self._selected_node)

    def _pause_debug(self):
        """暂停调试"""
        if not self._selected_node:
            return

        node_debugger.pause_debug(self._selected_node)

    def _resume_debug(self):
        """恢复调试"""
        if not self._selected_node:
            return

        node_debugger.resume_debug(self._selected_node)

    def _add_breakpoint(self):
        """添加日志断点"""
        pattern = self._bp_pattern.text().strip()
        action = self._bp_action.currentText()
        
        if not pattern or not self._selected_node:
            return

        node_debugger.set_log_breakpoint(self._selected_node, pattern, action)
        self._bp_pattern.clear()
        self._update_breakpoints()

    def _update_breakpoints(self):
        """更新断点列表"""
        if not self._selected_node:
            return

        session = node_debugger.get_session(self._selected_node)
        if not session:
            return

        self._bp_table.setRowCount(len(session.breakpoints))
        for i, bp in enumerate(session.breakpoints):
            self._bp_table.setItem(i, 0, QTableWidgetItem(bp.pattern))
            self._bp_table.setItem(i, 1, QTableWidgetItem(bp.action))
            self._bp_table.setItem(i, 2, QTableWidgetItem(str(bp.hit_count)))

    def _clear_breakpoints(self):
        """清除所有断点"""
        if not self._selected_node:
            return

        node_debugger.clear_log_breakpoints(self._selected_node)
        self._update_breakpoints()

    def _refresh_variables(self):
        """刷新变量"""
        self._update_variables()

    def _on_debug_start(self, data):
        """调试启动事件"""
        logger.info("Debug started: %s", data.get('node_name'))
        self._update_sessions()

    def _on_debug_stop(self, data):
        """调试停止事件"""
        logger.info("Debug stopped: %s", data.get('node_name'))
        self._update_sessions()

    def _on_debug_pause(self, data):
        """调试暂停事件"""
        logger.info("Debug paused: %s", data.get('node_name'))
        self._update_sessions()

    def _on_debug_resume(self, data):
        """调试恢复事件"""
        logger.info("Debug resumed: %s", data.get('node_name'))
        self._update_sessions()

    def _on_close(self):
        """面板关闭"""
        self._timer.stop()
        node_debugger.unsubscribe('debug.start', self._on_debug_start)
        node_debugger.unsubscribe('debug.stop', self._on_debug_stop)
        node_debugger.unsubscribe('debug.pause', self._on_debug_pause)
        node_debugger.unsubscribe('debug.resume', self._on_debug_resume)
        super()._on_close()

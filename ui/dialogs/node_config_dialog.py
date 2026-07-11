"""Node configuration dialog - config editor with two-way sync + real-time log viewer."""
import os
import sys
import json
import subprocess
import platform
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout, QLineEdit, 
    QPushButton, QTextEdit, QGroupBox, QScrollArea, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QColorDialog, QSlider, QSpinBox, QComboBox,
    QDialogButtonBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from ui.core.logger import logger
from ui.core.dock.floating_panel import FloatingPanel
from ui.core.i18n import t
from ui.core.utils.file_utils import resolve_and_open_folder
from ui.core.utils.dialog_utils import themed_message
from ui.core.system.polling_manager import polling_manager

class NodeConfigDialog(FloatingPanel):
    """Node configuration dialog - config editor with two-way sync + real-time log viewer."""
    
    def __init__(self, node_name, config, node_path, parent_window=None):
        super().__init__(parent_window, title=f"Node Config: {node_name}")
        self.node_name = node_name
        self.config = config
        self.node_path = node_path

        # ---- Config editor two-way sync state ----
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._write_config_to_file)
        self._last_config_content = ""
        self._ignore_external = False

        # ---- Log auto-refresh state ----
        self._current_log_file = ""

        self.resize(950, 550)
        self.setMinimumSize(700, 400)
        self._init_ui()

        # ---- Subscribe to polling_manager signals (replaces standalone timers) ----
        polling_manager.config_file_changed.connect(self._on_config_external_change)
        polling_manager.log_file_changed.connect(self._on_log_external_change)
        polling_manager.node_status_changed.connect(self._on_node_status_changed)
        polling_manager.watch_config(self.node_path)
        
    def _init_ui(self):
        """Initialize UI."""
        
        # Main horizontal layout: left JSON editor + right controls
        main_h_layout = QHBoxLayout()
        main_h_layout.setSpacing(10)
        
        # ===== Left area: upper and lower JSON editors =====
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)
        
        # Upper: config.json editor
        config_group = QGroupBox(t("k_config_edit"))
        config_layout = QVBoxLayout(config_group)

        # Toolbar: status indicator
        tool_row = QHBoxLayout()
        self._config_status = QLabel("")
        self._config_status.setStyleSheet("color: rgba(255,255,255,120); font-size: 10px; background: transparent;")
        tool_row.addWidget(self._config_status)
        tool_row.addStretch()
        config_layout.addLayout(tool_row)
        
        self.config_text = QTextEdit()
        self.config_text.setReadOnly(False)
        self.config_text.setFont(QFont("Consolas", 10))
        self.config_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                selection-background-color: #264f78;
            }
        """)
        # User edits text -> debounced save
        self.config_text.textChanged.connect(self._on_config_edit)
        
        # Load and display config.json content
        self.load_config_json()
        
        config_layout.addWidget(self.config_text)
        
        left_layout.addWidget(config_group, 1)
        
        # Lower: log viewer
        log_group = QGroupBox("Node Log")
        log_layout = QVBoxLayout(log_group)
        
        # Log file selector dropdown
        log_file_layout = QHBoxLayout()
        log_file_label = QLabel("Log File:")
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
        
        # Clear log button
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.setStyleSheet("background-color: #666666; color: white; padding: 5px 15px;")
        self.clear_log_btn.clicked.connect(self.clear_current_log)
        log_file_layout.addWidget(self.clear_log_btn)
        
        log_layout.addLayout(log_file_layout)
        
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
        
        # Load and display log file list
        self.load_log_files()
        
        log_layout.addWidget(self.output_text)
        
        left_layout.addWidget(log_group, 1)
        
        main_h_layout.addLayout(left_layout, 2)
        
        # ===== Right area: node controls and tools =====
        right_layout = QVBoxLayout()
        right_layout.setSpacing(10)
        
        # Node info card
        info_group = QGroupBox("Node Info")
        info_layout = QVBoxLayout(info_group)
        
        node_name_label = QLabel(f"Name: {self.node_name}")
        node_name_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        info_layout.addWidget(node_name_label)
        
        # Status display label
        self._status_label = QLabel("Status: detecting...")
        self._status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        info_layout.addWidget(self._status_label)
        
        node_path_label = QLabel(f"Path: {self.node_path}")
        node_path_label.setFont(QFont("Arial", 9))
        node_path_label.setWordWrap(True)
        info_layout.addWidget(node_path_label)
        
        right_layout.addWidget(info_group)
        
        # Initialize status display
        self._update_status_display()
        
        # Node control buttons
        control_group = QGroupBox("Node Control")
        control_layout = QVBoxLayout(control_group)
        
        # Start button
        start_btn = QPushButton("Start Node")
        start_btn.setStyleSheet("background-color: #333333; color: white; padding: 12px; font-weight: bold; font-size: 13px;")
        start_btn.clicked.connect(self.start_node)
        control_layout.addWidget(start_btn)
        
        # Stop button
        stop_btn = QPushButton("Stop Node")
        stop_btn.setStyleSheet("background-color: #555555; color: white; padding: 12px; font-weight: bold; font-size: 13px;")
        stop_btn.clicked.connect(self.stop_node)
        control_layout.addWidget(stop_btn)
        
        control_layout.addSpacing(10)
        
        right_layout.addWidget(control_group)
        
        # Quick actions
        quick_group = QGroupBox("Quick Actions")
        quick_layout = QVBoxLayout(quick_group)
        
        # Open folder button
        open_folder_btn = QPushButton("Open Folder")
        open_folder_btn.setStyleSheet("background-color: #666666; color: white; padding: 10px;")
        open_folder_btn.clicked.connect(self.open_node_folder)
        quick_layout.addWidget(open_folder_btn)
        
        # Open terminal button
        open_terminal_btn = QPushButton("Open Terminal")
        open_terminal_btn.setStyleSheet("background-color: #666666; color: white; padding: 10px;")
        open_terminal_btn.clicked.connect(self.open_terminal)
        quick_layout.addWidget(open_terminal_btn)
        
        # IDE open button (unified IDEScanner, no external hardcoding)
        from ui.core.node.ide_scanner import ide_scanner
        ide_scanner._app_config = self.parent_window.app_config if self.parent_window and hasattr(self.parent_window, 'app_config') else None
        ide_scanner.add_buttons_to_layout(quick_layout, self.node_name, self.node_path)
        
        right_layout.addWidget(quick_group)
        
        right_layout.addStretch()
        
        main_h_layout.addLayout(right_layout, 1)
        
        self.content_layout.addLayout(main_h_layout)
    
    def _update_status_display(self):
        """Update status display label."""
        if not self.parent_window:
            self._status_label.setText("Status: unknown")
            self._status_label.setStyleSheet("color: gray;")
            return
        
        node_data = self.parent_window.nodes_data.get(self.node_name)
        if not node_data:
            self._status_label.setText("Status: not found")
            self._status_label.setStyleSheet("color: gray;")
            return
        
        status = node_data.get('status', 'unknown')
        if status == 'running':
            self._status_label.setText("Status: Running")
            self._status_label.setStyleSheet("color: #FF4444;")
        elif status == 'idle':
            self._status_label.setText("Status: Idle")
            self._status_label.setStyleSheet("color: #44FF44;")
        else:
            self._status_label.setText("Status: Stopped")
            self._status_label.setStyleSheet("color: gray;")
    
    def _on_node_status_changed(self, node_name, new_status):
        """polling_manager signal: node status changed."""
        if node_name == self.node_name:
            self._update_status_display()
    
    def start_node(self):
        """Start node (dialog stays open)."""
        if not self.parent_window:
            return
        
        node_data = self.parent_window.nodes_data.get(self.node_name)
        if node_data and node_data.get('status') in ('running', 'idle'):
            themed_message(self, t("k_title_info"), t("k_node_already_running"), "info")
            return
        
        try:
            self.parent_window.start_selected_node_by_name(self.node_name)
            self._update_status_display()
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_node_start_fail_prop").format(err=str(e)), "error")
    
    def stop_node(self):
        """Stop node (dialog stays open)."""
        if not self.parent_window:
            return
        
        node_data = self.parent_window.nodes_data.get(self.node_name)
        if not node_data or node_data.get('status') == 'stopped':
            themed_message(self, t("k_title_info"), t("k_node_not_running"), "info")
            return
        
        try:
            self.parent_window.stop_selected_node_by_name(self.node_name)
            self._update_status_display()
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_node_stop_fail_prop").format(err=str(e)), "error")
    
    def open_node_folder(self):
        """Open node folder."""
        from ui.core.utils.file_utils import resolve_and_open_folder
        resolve_and_open_folder(
            self.node_path,
            self.node_name,
            parent_window=self.parent_window,
            dialog_parent=self
        )
    
    def open_terminal(self):
        """Open terminal with venv activated."""
        try:
            if platform.system() == "Windows":
                activate_script = os.path.join(self.node_path, "venv", "Scripts", "activate.bat")
            else:
                activate_script = os.path.join(self.node_path, "venv", "bin", "activate")
            
            if not os.path.exists(activate_script):
                themed_message(self, t("k_title_warning"), t("_k_venv_not_exist").format(path=activate_script), "warning")
                return
            
            system = platform.system()
            if system == "Windows":
                cmd = f'start cmd /k "cd /d {self.node_path} && call venv\\Scripts\\activate.bat && echo Virtual environment activated && echo Current dir: %CD% && echo Python path: where python"'
                subprocess.Popen(cmd, shell=True)
            elif system == "Darwin":  # macOS
                script = f'''tell application "Terminal"
                    do script "cd '{self.node_path}' && source venv/bin/activate && echo 'Virtual environment activated' && echo 'Current dir: $PWD' && echo 'Python path: $(which python)'"
                end tell'''
                subprocess.Popen(['osascript', '-e', script])
            else:  # Linux
                terminals = ['gnome-terminal', 'konsole', 'xterm']
                for terminal in terminals:
                    try:
                        cmd = f"cd '{self.node_path}' && source venv/bin/activate && echo 'Virtual environment activated' && exec bash"
                        subprocess.Popen([terminal, '-e', f'bash -c "{cmd}"'])
                        break
                    except Exception:
                        continue
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_terminal_open_fail").format(err=str(e)), "error")
            import traceback
            traceback.print_exc()
    
    # ==================== config.json two-way sync ====================

    def load_config_json(self):
        """Load config.json from file into editor (without triggering textChanged save)."""
        config_path = os.path.join(self.node_path, "config.json")
        try:
            if not os.path.exists(config_path):
                self.config_text.blockSignals(True)
                self.config_text.setPlainText("{}")
                self.config_text.blockSignals(False)
                self._last_config_content = "{}"
                return

            with open(config_path, 'r', encoding='utf-8') as f:
                raw = f.read()

            if not raw.strip():
                formatted = "{}"
            else:
                try:
                    data = json.loads(raw)
                    formatted = json.dumps(data, indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    formatted = raw

            self._last_config_content = formatted
            self.config_text.blockSignals(True)
            self.config_text.setPlainText(formatted)
            self.config_text.blockSignals(False)

        except Exception:
            self._last_config_content = ""

    def _on_config_edit(self):
        """User edit -> debounced save."""
        self._save_timer.start(800)

    def _write_config_to_file(self):
        """Write editor content to config.json (debounced save)."""
        if self._ignore_external:
            return

        config_path = os.path.join(self.node_path, "config.json")
        content = self.config_text.toPlainText().strip()

        if not content:
            return

        try:
            try:
                data = json.loads(content)
                formatted = json.dumps(data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                formatted = content

            self._last_config_content = formatted
            self._ignore_external = True

            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(formatted)

            # Sync editor to formatted content (prevent loopback)
            self.config_text.blockSignals(True)
            self.config_text.setPlainText(formatted)
            self.config_text.blockSignals(False)

            # Update in-memory data
            if self.parent_window and self.node_name in self.parent_window.nodes_data:
                try:
                    self.parent_window.nodes_data[self.node_name]['config'] = data
                except Exception:
                    pass
                if hasattr(self.parent_window, 'canvas'):
                    self.parent_window.canvas.sync_node_display(self.node_name)

            self._config_status.setText(t("k_status_saved"))
            self._config_status.setStyleSheet("color: #4CAF50; font-size: 10px; background: transparent;")

            QTimer.singleShot(500, self._reset_ignore_flag)

        except Exception as e:
            self._config_status.setText(t("k_status_save_failed"))
            self._config_status.setStyleSheet("color: #F44336; font-size: 10px; background: transparent;")
            logger.error("Failed to save config.json: %s", e)

    def _reset_ignore_flag(self):
        self._ignore_external = False

    def _on_config_external_change(self, node_path):
        """polling_manager signal: config.json was modified externally."""
        if node_path != self.node_path or self._ignore_external:
            return
        self.load_config_json()
        self._config_status.setText(t("k_status_updated"))
        self._config_status.setStyleSheet("color: #2196F3; font-size: 10px; background: transparent;")

    # ==================== Log dynamic refresh ====================

    def _on_log_external_change(self, node_path, log_filename):
        """polling_manager signal: log file was modified externally."""
        if node_path != self.node_path or not self._current_log_file:
            return
        if log_filename == self._current_log_file:
            self._load_log_content(log_filename)

    def _load_log_content(self, log_filename):
        """Load log file content into editor."""
        log_path = os.path.join(self.node_path, "logs", log_filename)
        try:
            if not os.path.exists(log_path):
                self.output_text.setPlainText(f"# Log file not found: {log_filename}")
                return

            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            if not content.strip():
                self.output_text.setPlainText(t("k_log_empty"))
            else:
                self.output_text.setPlainText(content)
            scrollbar = self.output_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except Exception:
            pass

    def load_log_files(self):
        """Load all .log files from logs directory."""
        try:
            logs_dir = os.path.join(self.node_path, "logs")
            
            if not os.path.exists(logs_dir):
                self.output_text.setPlainText("# logs directory does not exist\n# Tip: the log directory and files are created automatically when the node starts")
                self._current_log_file = ""
                self.log_file_combo.blockSignals(True)
                self.log_file_combo.clear()
                self.log_file_combo.blockSignals(False)
                return
            
            log_files = sorted([f for f in os.listdir(logs_dir) if f.endswith('.log')])
            
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
                polling_manager.watch_log(self.node_path, self._current_log_file)
                self._load_log_content(self._current_log_file)
                
        except Exception:
            pass
    
    def on_log_file_changed(self, index):
        """Load corresponding log when selection changes."""
        if index >= 0:
            if self._current_log_file:
                polling_manager.unwatch_log(self.node_path, self._current_log_file)
            log_filename = self.log_file_combo.itemText(index)
            self._current_log_file = log_filename
            polling_manager.watch_log(self.node_path, log_filename)
            self._load_log_content(log_filename)
    
    def clear_current_log(self):
        """Clear current log file."""
        if self.log_file_combo.count() == 0:
            themed_message(self, t("k_title_warning"), t("k_log_no_clear"), "warning")
            return
        
        log_filename = self.log_file_combo.currentText()
        logs_dir = os.path.join(self.node_path, "logs")
        log_path = os.path.join(logs_dir, log_filename)
        
        reply = themed_message(self, t("k_title_confirm_clear"), t("_k_clear_log_file_confirm").format(name=log_filename),
            "question")
        
        if reply:
            try:
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write("")
                self._last_log_mtime = os.path.getmtime(log_path)
                self.output_text.setPlainText(t("k_log_cleared"))
            except Exception as e:
                themed_message(self, t("k_title_error"), t("_k_log_file_clear_fail").format(err=str(e)), "error")

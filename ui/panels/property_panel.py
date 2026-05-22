"""
属性配置面板 - 右侧面板，显示和编辑节点配置
"""
import os
import json
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout, QLineEdit, QPushButton, QTextEdit, QGroupBox, QScrollArea, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox)
from ui.core.utils.dialog_utils import themed_message
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from ui.core.logger import logger
from ui.core.i18n import t
from ui.dialogs.node_config_dialog import NodeConfigDialog

class PropertyPanel(QWidget):
    """属性配置面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        
        self.current_node_name = None
        self.current_node_path = None
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(10)
        self.content_layout.addStretch()
        
        scroll.setWidget(self.content_widget)
        self.layout.addWidget(scroll)
        
        # 初始状态：显示提示信息
        self.show_default_info()
    
    def show_default_info(self):
        """显示默认信息（未选中节点时）"""
        self.clear_content()
        
        title = QLabel(t("k_properties"))
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.insertWidget(0, title)
        
        info_label = QLabel(t("k_no_selection"))
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.insertWidget(1, info_label)
    
    def clear_content(self):
        """清除所有内容"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def load_node_config(self, node_name, config, node_path):
        """加载节点配置"""
        self.clear_content()
        self.current_node_name = node_name
        self.current_node_path = node_path
        
        # 标题
        title = QLabel(f"节点: {node_name}")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.content_layout.addWidget(title)
        
        # 基本配置
        basic_config = QGroupBox(t("k_basic_config"))
        config_layout = QFormLayout(basic_config)
        
        node_name_edit = QLineEdit(str(config.get('node_name', '')))
        node_name_edit.setReadOnly(True)
        config_layout.addRow(t("k_field_node_name"), node_name_edit)
        
        listen_file_edit = QLineEdit(str(config.get('listen_upper_file', '')))
        listen_file_edit.setReadOnly(True)
        config_layout.addRow(t("k_field_listen_file"), listen_file_edit)
        
        output_file_edit = QLineEdit(str(config.get('output_file', '')))
        output_file_edit.setReadOnly(True)
        config_layout.addRow(t("k_field_output_file"), output_file_edit)
        
        output_type_edit = QLineEdit(str(config.get('output_type', '')))
        output_type_edit.setReadOnly(True)
        config_layout.addRow(t("k_field_output_type"), output_type_edit)
        
        self.content_layout.addWidget(basic_config)
        
        # Filter规则表格
        filter_group = QGroupBox(t("k_filter_rules"))
        filter_layout = QVBoxLayout(filter_group)
        
        self.filter_table = QTableWidget()
        self.filter_table.setColumnCount(2)
        self.filter_table.setHorizontalHeaderLabels(["Key", "Value"])
        self.filter_table.horizontalHeader().setStretchLastSection(True)
        self.filter_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        filter_rules = config.get('filter', {})
        if isinstance(filter_rules, dict):
            self.filter_table.setRowCount(len(filter_rules))
            for row, (key, value) in enumerate(filter_rules.items()):
                self.filter_table.setItem(row, 0, QTableWidgetItem(str(key)))
                self.filter_table.setItem(row, 1, QTableWidgetItem(str(value)))
        elif isinstance(filter_rules, list):
            self.filter_table.setRowCount(len(filter_rules))
            for row, rule in enumerate(filter_rules):
                if isinstance(rule, dict):
                    key = rule.get('key', '')
                    value = rule.get('value', '')
                    self.filter_table.setItem(row, 0, QTableWidgetItem(str(key)))
                    self.filter_table.setItem(row, 1, QTableWidgetItem(str(value)))
        else:
            self.filter_table.setRowCount(0)
        
        filter_layout.addWidget(self.filter_table)
        
        # Filter操作按钮
        filter_btn_layout = QHBoxLayout()
        
        add_btn = QPushButton(t("k_add_rule"))
        add_btn.clicked.connect(self.add_filter_rule)
        filter_btn_layout.addWidget(add_btn)
        
        del_btn = QPushButton(t("k_delete_selected"))
        del_btn.clicked.connect(self.delete_filter_rule)
        filter_btn_layout.addWidget(del_btn)
        
        filter_layout.addLayout(filter_btn_layout)
        self.content_layout.addWidget(filter_group)
        
        # 节点控制
        control_group = QGroupBox(t("k_node_control"))
        control_layout = QVBoxLayout(control_group)
        
        start_btn = QPushButton(t("k_node_start"))
        start_btn.clicked.connect(self.start_node)
        control_layout.addWidget(start_btn)
        
        stop_btn = QPushButton(t("k_node_stop"))
        stop_btn.clicked.connect(self.stop_node)
        control_layout.addWidget(stop_btn)
        
        self.content_layout.addWidget(control_group)
        
        # 保存按钮
        save_btn = QPushButton(t("k_config_save"))
        save_btn.clicked.connect(self.save_config)
        self.content_layout.addWidget(save_btn)
        
        self.content_layout.addStretch()
    
    def start_node(self):
        """启动节点"""
        if not self.current_node_name or not self.parent_window:
            themed_message(self, t("k_title_warning"), t("k_node_select_one"), "warning")
            return
        
        node_data = self.parent_window.nodes_data.get(self.current_node_name)
        if node_data and node_data.get('status') == 'running':
            themed_message(self, t("k_title_info"), t("k_node_already_running"), "info")
            return
        
        try:
            from ui.core.node_process import start_node_process
            start_path = self.current_node_path
            if os.path.exists(start_path):
                if os.path.exists(os.path.join(start_path, "start.bat")):
                    start_script = os.path.join(start_path, "start.bat")
                elif os.path.exists(os.path.join(start_path, "start.sh")):
                    start_script = os.path.join(start_path, "start.sh")
                else:
                    themed_message(self, t("k_title_error"), t("_k_start_script_missing").format(script=start_script), "error")
                    return
                start_node_process(self.parent_window.nodes_data[self.current_node_name])
                self.parent_window.nodes_data[self.current_node_name]['status'] = 'running'
                self.parent_window.canvas.update_node_status(self.current_node_name, 'running')
                self.parent_window.node_list_panel.update_node_status(self.current_node_name, 'running')
                themed_message(self, t("k_title_success"), t("_k_node_started_prop").format(name=self.current_node_name), "info")
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_node_start_fail_prop").format(err=str(e)), "error")
    
    def stop_node(self):
        """停止节点"""
        if not self.current_node_name or not self.parent_window:
            themed_message(self, t("k_title_warning"), t("k_node_select_one"), "warning")
            return
        
        node_data = self.parent_window.nodes_data.get(self.current_node_name)
        if not node_data or node_data.get('status') != 'running':
            themed_message(self, t("k_title_info"), t("k_node_not_running"), "info")
            return
        
        try:
            from ui.core.node_process import stop_node_process
            stop_node_process(self.parent_window.nodes_data[self.current_node_name])
            self.parent_window.nodes_data[self.current_node_name]['status'] = 'stopped'
            self.parent_window.canvas.update_node_status(self.current_node_name, 'stopped')
            self.parent_window.node_list_panel.update_node_status(self.current_node_name, 'stopped')
            themed_message(self, t("k_title_success"), t("_k_node_stopped_prop").format(name=self.current_node_name), "info")
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_node_stop_fail_prop").format(err=str(e)), "error")
    
    def add_filter_rule(self):
        """添加Filter规则"""
        row = self.filter_table.rowCount()
        self.filter_table.insertRow(row)
        self.filter_table.setItem(row, 0, QTableWidgetItem(""))
        self.filter_table.setItem(row, 1, QTableWidgetItem(""))
    
    def delete_filter_rule(self):
        """删除选中的Filter规则"""
        current_row = self.filter_table.currentRow()
        if current_row >= 0:
            self.filter_table.removeRow(current_row)
    
    def save_config(self):
        """保存配置"""
        if not self.current_node_name or not self.current_node_path:
            themed_message(self, t("k_title_warning"), t("k_node_select_one"), "warning")
            return
        
        try:
            import os
            config_path = os.path.join(self.current_node_path, "config.json")
            
            # 读取当前配置
            config = {}
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.loads(f.read())
            
            # 保存Filter规则
            filter_rules = {}
            for row in range(self.filter_table.rowCount()):
                key_item = self.filter_table.item(row, 0)
                value_item = self.filter_table.item(row, 1)
                if key_item and value_item:
                    key = key_item.text().strip()
                    value = value_item.text().strip()
                    if key and value:
                        filter_rules[key] = value
            
            config['filter'] = filter_rules
            
            # 写入文件
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 更新内存数据
            if self.parent_window and self.current_node_name in self.parent_window.nodes_data:
                self.parent_window.nodes_data[self.current_node_name]['config'] = config
                if hasattr(self.parent_window, 'canvas'):
                    self.parent_window.canvas.sync_node_display(self.current_node_name)
            
            themed_message(self, t("k_title_success"), t("k_config_saved"), "info")
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_config_save_fail").format(err=str(e)), "error")
            
    def load_connection_info(self, source_name, target_name, source_output_path):
        """加载连线配置信息"""
        self.clear_content()
        self.current_node_name = None
        self.current_node_path = None
        
        title = QLabel(t("k_connection_config"))
        title.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.content_layout.addWidget(title)
        
        info_group = QGroupBox(t("k_connection_details"))
        info_layout = QFormLayout(info_group)
        
        upstream_label = QLabel(source_name)
        info_layout.addRow(t("k_upstream_node"), upstream_label)
        
        downstream_label = QLabel(target_name)
        info_layout.addRow(t("k_downstream_node"), downstream_label)
        
        path_label = QLabel(source_output_path)
        path_label.setWordWrap(True)
        info_layout.addRow(t("k_upstream_path"), path_label)
        
        self.content_layout.addWidget(info_group)
        
        note = QLabel(
            "说明:\n"
            "- 上游节点的 output.json 路径已自动配置到下游节点\n"
            "- 删除连线将清空下游节点的 listen_upper_file 配置"
        )
        note.setStyleSheet("padding: 10px; background-color: #fff3cd; border-radius: 5px;")
        note.setWordWrap(True)
        self.content_layout.addWidget(note)
        self.content_layout.addStretch()

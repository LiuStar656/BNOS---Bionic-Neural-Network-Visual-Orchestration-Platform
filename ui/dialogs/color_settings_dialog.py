"""画布和节点颜色设置对话框"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout,
    QPushButton, QGroupBox, QScrollArea, QColorDialog, QSlider, QSpinBox, QDialog)
from ui.core.utils.dialog_utils import themed_message
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from ui.core.i18n import t

_STYLE = """
QDialog { background-color: #2d2d30; border: 1px solid #555; border-radius: 6px; }
QGroupBox { color: #ccc; font-weight: bold; border: 1px solid #454545; border-radius: 4px; margin-top: 8px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QLabel { color: #ccc; }
QScrollArea { border: none; background: transparent; }
QSlider::groove:horizontal { height: 6px; background: #333; border-radius: 3px; }
QSlider::handle:horizontal { width: 14px; height: 14px; background: #777; border-radius: 7px; margin: -4px 0; }
QSpinBox { background: #3c3c3c; color: #ccc; border: 1px solid #555; padding: 3px; }
"""

class ColorSettingsDialog(QDialog):
    """画布和节点颜色设置对话框"""

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setWindowTitle(t("k_color_settings"))
        self.setFixedSize(500, 580)
        self.setStyleSheet(_STYLE)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self._drag_pos = None

        self.init_ui()
        if parent:
            self.move(parent.geometry().center() - self.rect().center())

    def mousePressEvent(self, e):
        if e.position().y() < 40:
            self._drag_pos = e.globalPosition().toPoint()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_pos:
            delta = e.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = e.globalPosition().toPoint()
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        super().mouseReleaseEvent(e)
        
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 10, 14, 10)

        # 自定义标题栏
        title_bar = QHBoxLayout()
        title = QLabel(t("k_color_settings"))
        title.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        title_bar.addWidget(title)
        title_bar.addStretch()
        cl = QLabel("✕")
        cl.setStyleSheet("color: #888; font-size: 14px; padding: 2px 6px;")
        cl.setCursor(Qt.CursorShape.PointingHandCursor)
        cl.mousePressEvent = lambda e: self.reject()
        title_bar.addWidget(cl)
        layout.addLayout(title_bar)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # ===== 画布背景色设置 =====
        canvas_group = QGroupBox(t("k_color_canvas_bg"))
        canvas_layout = QFormLayout(canvas_group)
        
        # 画布背景色
        self.canvas_color_btn = QPushButton(t("k_color_select"))
        self.canvas_color_btn.setStyleSheet(f"background-color: {self.canvas.canvas_bg_color}; min-height: 30px;")
        self.canvas_color_btn.clicked.connect(lambda: self.choose_color('canvas'))
        canvas_layout.addRow(t("k_field_bg_color"), self.canvas_color_btn)
        
        # 网格线颜色
        self.grid_color_btn = QPushButton(t("k_color_select"))
        self.grid_color_btn.setStyleSheet(f"background-color: {self.canvas.grid_color}; min-height: 30px;")
        self.grid_color_btn.clicked.connect(lambda: self.choose_color('grid'))
        canvas_layout.addRow(t("k_field_grid_color"), self.grid_color_btn)
        
        # 网格线透明度
        self.grid_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.grid_opacity_slider.setRange(0, 100)
        self.grid_opacity_slider.setValue(int(self.canvas.grid_opacity * 100))
        self.grid_opacity_slider.valueChanged.connect(self.update_grid_opacity_label)
        self.grid_opacity_label = QLabel(f"{int(self.canvas.grid_opacity * 100)}%")
        grid_opacity_layout = QVBoxLayout()
        grid_opacity_layout.addWidget(self.grid_opacity_slider)
        grid_opacity_layout.addWidget(self.grid_opacity_label)
        canvas_layout.addRow(t("k_field_grid_opacity"), grid_opacity_layout)
        
        content_layout.addWidget(canvas_group)
        
        # ===== 节点样式设置 =====
        node_group = QGroupBox(t("k_color_node_style"))
        node_layout = QFormLayout(node_group)
        
        # 节点背景色
        self.node_bg_btn = QPushButton(t("k_color_select"))
        self.node_bg_btn.setStyleSheet(f"background-color: {self.canvas.node_bg_color}; min-height: 30px;")
        self.node_bg_btn.clicked.connect(lambda: self.choose_color('node_bg'))
        node_layout.addRow(t("k_field_node_bg"), self.node_bg_btn)
        
        # 节点边框色
        self.node_border_btn = QPushButton(t("k_color_select"))
        self.node_border_btn.setStyleSheet(f"background-color: {self.canvas.node_border_color}; min-height: 30px;")
        self.node_border_btn.clicked.connect(lambda: self.choose_color('node_border'))
        node_layout.addRow(t("k_field_node_border"), self.node_border_btn)
        
        # 节点文字颜色
        self.node_text_btn = QPushButton(t("k_color_select"))
        self.node_text_btn.setStyleSheet(f"background-color: {self.canvas.node_text_color}; min-height: 30px;")
        self.node_text_btn.clicked.connect(lambda: self.choose_color('node_text'))
        node_layout.addRow(t("k_field_node_text"), self.node_text_btn)
        
        # 选中节点边框色
        self.node_selected_btn = QPushButton(t("k_color_select"))
        self.node_selected_btn.setStyleSheet(f"background-color: {self.canvas.node_selected_color}; min-height: 30px;")
        self.node_selected_btn.clicked.connect(lambda: self.choose_color('node_selected'))
        node_layout.addRow(t("k_field_selected_border"), self.node_selected_btn)
        
        content_layout.addWidget(node_group)
        
        # ===== 锚点样式设置 =====
        anchor_group = QGroupBox(t("k_color_anchor_style"))
        anchor_layout = QFormLayout(anchor_group)
        
        # 输入锚点颜色
        self.input_anchor_btn = QPushButton(t("k_color_select"))
        self.input_anchor_btn.setStyleSheet(f"background-color: {self.canvas.input_anchor_color}; min-height: 30px;")
        self.input_anchor_btn.clicked.connect(lambda: self.choose_color('input_anchor'))
        anchor_layout.addRow(t("k_field_input_anchor"), self.input_anchor_btn)
        
        # 输出锚点颜色
        self.output_anchor_btn = QPushButton(t("k_color_select"))
        self.output_anchor_btn.setStyleSheet(f"background-color: {self.canvas.output_anchor_color}; min-height: 30px;")
        self.output_anchor_btn.clicked.connect(lambda: self.choose_color('output_anchor'))
        anchor_layout.addRow(t("k_field_output_anchor"), self.output_anchor_btn)
        
        content_layout.addWidget(anchor_group)
        
        # ===== 连线样式设置 =====
        edge_group = QGroupBox(t("k_color_edge_style"))
        edge_layout = QFormLayout(edge_group)
        
        # 连线颜色
        self.edge_color_btn = QPushButton(t("k_color_select"))
        self.edge_color_btn.setStyleSheet(f"background-color: {self.canvas.edge_color}; min-height: 30px;")
        self.edge_color_btn.clicked.connect(lambda: self.choose_color('edge'))
        edge_layout.addRow(t("k_field_edge_color"), self.edge_color_btn)
        
        # 连线宽度
        self.edge_width_spinbox = QSpinBox()
        self.edge_width_spinbox.setRange(1, 10)
        self.edge_width_spinbox.setValue(self.canvas.edge_width)
        edge_layout.addRow(t("k_field_edge_width"), self.edge_width_spinbox)
        
        content_layout.addWidget(edge_group)
        
        # ===== 预设主题 =====
        theme_group = QGroupBox(t("k_color_quick_theme"))
        theme_layout = QVBoxLayout(theme_group)
        
        theme_btn_layout = QVBoxLayout()
        
        # 深色主题（VSCode 默认）
        dark_theme_btn = QPushButton(t("k_color_dark_theme"))
        dark_theme_btn.clicked.connect(lambda: self.apply_preset_theme('dark'))
        theme_btn_layout.addWidget(dark_theme_btn)
        
        # 浅色主题
        light_theme_btn = QPushButton(t("k_color_light_theme"))
        light_theme_btn.clicked.connect(lambda: self.apply_preset_theme('light'))
        theme_btn_layout.addWidget(light_theme_btn)
        
        theme_layout.addLayout(theme_btn_layout)
        
        content_layout.addWidget(theme_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()

        # 应用按钮（不关闭）
        apply_btn = QPushButton(t("k_color_apply"))
        apply_btn.setStyleSheet("background-color: #333333; color: white; padding: 8px 16px; font-weight: bold;")
        apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_btn)

        # 确认按钮（应用+关闭）
        confirm_btn = QPushButton(t("k_ok"))
        confirm_btn.setStyleSheet("background-color: #0e639c; color: white; padding: 8px 24px; font-weight: bold;")
        confirm_btn.clicked.connect(self.confirm_and_close)
        button_layout.addWidget(confirm_btn)

        # 重置按钮
        reset_btn = QPushButton(t("k_color_reset"))
        reset_btn.setStyleSheet("background-color: #555555; color: white; padding: 8px 16px;")
        reset_btn.clicked.connect(self.reset_to_default)
        button_layout.addWidget(reset_btn)

        # 关闭按钮
        close_btn = QPushButton(t("k_cancel"))
        close_btn.setStyleSheet("background-color: #444444; color: #ccc; padding: 8px 16px;")
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)

        content_layout.addLayout(button_layout)
        
    def update_grid_opacity_label(self, value):
        """更新网格线透明度标签"""
        self.grid_opacity_label.setText(f"{value}%")
        
    def choose_color(self, target):
        """选择颜色"""
        from PyQt6.QtWidgets import QColorDialog
        
        # 获取当前颜色
        current_colors = {
            'canvas': self.canvas.canvas_bg_color,
            'grid': self.canvas.grid_color,
            'node_bg': self.canvas.node_bg_color,
            'node_border': self.canvas.node_border_color,
            'node_text': self.canvas.node_text_color,
            'node_selected': self.canvas.node_selected_color,
            'input_anchor': self.canvas.input_anchor_color,
            'output_anchor': self.canvas.output_anchor_color,
            'edge': self.canvas.edge_color
        }
        
        current_color = QColor(current_colors[target])
        new_color = QColorDialog.getColor(current_color, self, t("k_color_select"))
        
        if new_color.isValid():
            color_hex = new_color.name()
            
            # 更新按钮显示
            btn_map = {
                'canvas': self.canvas_color_btn,
                'grid': self.grid_color_btn,
                'node_bg': self.node_bg_btn,
                'node_border': self.node_border_btn,
                'node_text': self.node_text_btn,
                'node_selected': self.node_selected_btn,
                'input_anchor': self.input_anchor_btn,
                'output_anchor': self.output_anchor_btn,
                'edge': self.edge_color_btn
            }
            
            btn_map[target].setStyleSheet(f"background-color: {color_hex}; min-height: 30px;")
            
            # 临时存储新颜色
            setattr(self, f'temp_{target}_color', color_hex)
            
    def apply_preset_theme(self, theme_name):
        """应用预设主题"""
        themes = {
            'dark': {
                'canvas_bg_color': '#1e1e1e',
                'grid_color': '#2a2a2a',
                'grid_opacity': 0.3,
                'node_bg_color': '#2d2d30',
                'node_border_color': '#454545',
                'node_text_color': '#d4d4d4',
                'node_selected_color': '#007acc',
                'input_anchor_color': '#6a9955',
                'output_anchor_color': '#007acc',
                'edge_color': '#007acc',
                'edge_width': 2
            },
            'light': {
                'canvas_bg_color': '#f3f3f3',
                'grid_color': '#e5e5e5',
                'grid_opacity': 0.4,
                'node_bg_color': '#ffffff',
                'node_border_color': '#d4d4d4',
                'node_text_color': '#333333',
                'node_selected_color': '#007acc',
                'input_anchor_color': '#388a34',
                'output_anchor_color': '#007acc',
                'edge_color': '#007acc',
                'edge_width': 2
            }
        }
        
        theme = themes.get(theme_name)
        if theme:
            # 应用主题到临时变量
            for key, value in theme.items():
                setattr(self, f'temp_{key}', value)
                
            # 更新按钮显示
            self.canvas_color_btn.setStyleSheet(f"background-color: {theme['canvas_bg_color']}; min-height: 30px;")
            self.grid_color_btn.setStyleSheet(f"background-color: {theme['grid_color']}; min-height: 30px;")
            self.grid_opacity_slider.setValue(int(theme['grid_opacity'] * 100))
            self.grid_opacity_label.setText(f"{int(theme['grid_opacity'] * 100)}%")
            self.node_bg_btn.setStyleSheet(f"background-color: {theme['node_bg_color']}; min-height: 30px;")
            self.node_border_btn.setStyleSheet(f"background-color: {theme['node_border_color']}; min-height: 30px;")
            self.node_text_btn.setStyleSheet(f"background-color: {theme['node_text_color']}; min-height: 30px;")
            self.node_selected_btn.setStyleSheet(f"background-color: {theme['node_selected_color']}; min-height: 30px;")
            self.input_anchor_btn.setStyleSheet(f"background-color: {theme['input_anchor_color']}; min-height: 30px;")
            self.output_anchor_btn.setStyleSheet(f"background-color: {theme['output_anchor_color']}; min-height: 30px;")
            self.edge_color_btn.setStyleSheet(f"background-color: {theme['edge_color']}; min-height: 30px;")
            self.edge_width_spinbox.setValue(theme['edge_width'])
            
    def collect_settings(self):
        """收集当前所有颜色设置（供 apply 和 confirm 共用）"""
        return {
            'canvas_bg_color': getattr(self, 'temp_canvas_bg_color', self.canvas.canvas_bg_color),
            'grid_color': getattr(self, 'temp_grid_color', self.canvas.grid_color),
            'grid_opacity': self.grid_opacity_slider.value() / 100.0,
            'node_bg_color': getattr(self, 'temp_node_bg_color', self.canvas.node_bg_color),
            'node_border_color': getattr(self, 'temp_node_border_color', self.canvas.node_border_color),
            'node_text_color': getattr(self, 'temp_node_text_color', self.canvas.node_text_color),
            'node_selected_color': getattr(self, 'temp_node_selected_color', self.canvas.node_selected_color),
            'input_anchor_color': getattr(self, 'temp_input_anchor_color', self.canvas.input_anchor_color),
            'output_anchor_color': getattr(self, 'temp_output_anchor_color', self.canvas.output_anchor_color),
            'edge_color': getattr(self, 'temp_edge_color', self.canvas.edge_color),
            'edge_width': self.edge_width_spinbox.value()
        }

    def apply_settings(self):
        """应用颜色设置（不关闭窗口）"""
        try:
            settings = self.collect_settings()
            self.canvas.apply_color_settings(settings)
            self.canvas._save_color_settings()
            themed_message(self, t("k_title_success"), t("k_color_applied"), "info")
        except Exception as e:
            themed_message(self, t("k_title_error"),
                t("_k_config_save_fail").format(err=str(e)), "error")

    def confirm_and_close(self):
        """确认并关闭：应用设置后关闭窗口"""
        try:
            settings = self.collect_settings()
            self.canvas.apply_color_settings(settings)
            self.canvas._save_color_settings()
            self.accept()
        except Exception as e:
            themed_message(self, t("k_title_error"),
                t("_k_config_save_fail").format(err=str(e)), "error")
            
    def reset_to_default(self):
        """恢复到默认颜色"""
        self.apply_preset_theme('dark')
        themed_message(self, t("k_title_info"), t("k_color_reset_done"), "info")

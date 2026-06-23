"""画布和节点颜色设置对话框 - 浮动窗口版本"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFormLayout,
    QPushButton, QGroupBox, QScrollArea, QColorDialog, QSlider, QSpinBox)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor
from ui.core.floating_panel import FloatingPanel
from ui.core.i18n import t
from ui.core.utils.dialog_utils import themed_message

_STYLE = """
QGroupBox { color: #ccc; font-weight: bold; border: 1px solid #454545; border-radius: 4px; margin-top: 8px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QLabel { color: #ccc; }
QScrollArea { border: none; background: transparent; }
QSlider::groove:horizontal { height: 6px; background: #333; border-radius: 3px; }
QSlider::handle:horizontal { width: 14px; height: 14px; background: #777; border-radius: 7px; margin: -4px 0; }
QSpinBox { background: #3c3c3c; color: #ccc; border: 1px solid #555; padding: 3px; }
"""

class ColorSettingsDialog(FloatingPanel):
    """画布和节点颜色设置对话框（浮动窗口版本）"""

    def __init__(self, parent=None):
        super().__init__(parent, title=t("k_color_settings"))
        self.parent_window = parent
        self.canvas = self._get_canvas()
        
        self.resize(500, 640)
        self.setStyleSheet(_STYLE)
        
        # 居中显示
        if parent:
            self.move(parent.geometry().center() - self.rect().center())

        self.init_ui()

    def _get_canvas(self):
        """获取当前活动的画布"""
        if hasattr(self.parent_window, '_canvas_host') and self.parent_window._canvas_host:
            ch = self.parent_window._canvas_host
            if hasattr(ch, 'canvas') and ch.canvas:
                return ch.canvas
            if hasattr(ch, 'get_active_canvas'):
                return ch.get_active_canvas()
        if hasattr(self.parent_window, 'canvas') and self.parent_window.canvas:
            return self.parent_window.canvas
        return None

    def init_ui(self):
        """初始化UI"""
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        scroll.setWidget(content_widget)
        self.content_layout.addWidget(scroll)
        
        # 获取当前颜色值（从canvas或使用默认值）
        colors = self._get_current_colors()
        
        # ===== 画布背景色设置 =====
        canvas_group = QGroupBox(t("k_color_canvas_bg"))
        canvas_layout = QFormLayout(canvas_group)
        
        # 画布背景色
        self.canvas_color_btn = QPushButton(t("k_color_select"))
        self.canvas_color_btn.setStyleSheet(f"background-color: {colors['canvas_bg_color']}; min-height: 30px;")
        self.canvas_color_btn.clicked.connect(lambda: self.choose_color('canvas_bg', colors['canvas_bg_color']))
        canvas_layout.addRow(t("k_field_bg_color"), self.canvas_color_btn)
        
        # 网格线颜色
        self.grid_color_btn = QPushButton(t("k_color_select"))
        self.grid_color_btn.setStyleSheet(f"background-color: {colors['grid_color']}; min-height: 30px;")
        self.grid_color_btn.clicked.connect(lambda: self.choose_color('grid', colors['grid_color']))
        canvas_layout.addRow(t("k_field_grid_color"), self.grid_color_btn)
        
        # 网格线透明度
        self.grid_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.grid_opacity_slider.setRange(0, 100)
        self.grid_opacity_slider.setValue(int(colors['grid_opacity'] * 100))
        self.grid_opacity_slider.valueChanged.connect(self.update_grid_opacity_label)
        self.grid_opacity_label = QLabel(f"{int(colors['grid_opacity'] * 100)}%")
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
        self.node_bg_btn.setStyleSheet(f"background-color: {colors['node_bg_color']}; min-height: 30px;")
        self.node_bg_btn.clicked.connect(lambda: self.choose_color('node_bg', colors['node_bg_color']))
        node_layout.addRow(t("k_field_node_bg"), self.node_bg_btn)
        
        # 节点边框色
        self.node_border_btn = QPushButton(t("k_color_select"))
        self.node_border_btn.setStyleSheet(f"background-color: {colors['node_border_color']}; min-height: 30px;")
        self.node_border_btn.clicked.connect(lambda: self.choose_color('node_border', colors['node_border_color']))
        node_layout.addRow(t("k_field_node_border"), self.node_border_btn)
        
        # 节点文字颜色
        self.node_text_btn = QPushButton(t("k_color_select"))
        self.node_text_btn.setStyleSheet(f"background-color: {colors['node_text_color']}; min-height: 30px;")
        self.node_text_btn.clicked.connect(lambda: self.choose_color('node_text', colors['node_text_color']))
        node_layout.addRow(t("k_field_node_text"), self.node_text_btn)
        
        # 选中节点边框色
        self.node_selected_btn = QPushButton(t("k_color_select"))
        self.node_selected_btn.setStyleSheet(f"background-color: {colors['node_selected_color']}; min-height: 30px;")
        self.node_selected_btn.clicked.connect(lambda: self.choose_color('node_selected', colors['node_selected_color']))
        node_layout.addRow(t("k_field_selected_border"), self.node_selected_btn)
        
        content_layout.addWidget(node_group)
        
        # ===== 锚点样式设置 =====
        anchor_group = QGroupBox(t("k_color_anchor_style"))
        anchor_layout = QFormLayout(anchor_group)
        
        # 输入锚点颜色
        self.input_anchor_btn = QPushButton(t("k_color_select"))
        self.input_anchor_btn.setStyleSheet(f"background-color: {colors['input_anchor_color']}; min-height: 30px;")
        self.input_anchor_btn.clicked.connect(lambda: self.choose_color('input_anchor', colors['input_anchor_color']))
        anchor_layout.addRow(t("k_field_input_anchor"), self.input_anchor_btn)
        
        # 输出锚点颜色
        self.output_anchor_btn = QPushButton(t("k_color_select"))
        self.output_anchor_btn.setStyleSheet(f"background-color: {colors['output_anchor_color']}; min-height: 30px;")
        self.output_anchor_btn.clicked.connect(lambda: self.choose_color('output_anchor', colors['output_anchor_color']))
        anchor_layout.addRow(t("k_field_output_anchor"), self.output_anchor_btn)
        
        content_layout.addWidget(anchor_group)
        
        # ===== 连线样式设置 =====
        edge_group = QGroupBox(t("k_color_edge_style"))
        edge_layout = QFormLayout(edge_group)
        
        # 连线颜色
        self.edge_color_btn = QPushButton(t("k_color_select"))
        self.edge_color_btn.setStyleSheet(f"background-color: {colors['edge_color']}; min-height: 30px;")
        self.edge_color_btn.clicked.connect(lambda: self.choose_color('edge', colors['edge_color']))
        edge_layout.addRow(t("k_field_edge_color"), self.edge_color_btn)
        
        # 连线宽度
        self.edge_width_spinbox = QSpinBox()
        self.edge_width_spinbox.setRange(1, 10)
        self.edge_width_spinbox.setValue(colors['edge_width'])
        edge_layout.addRow(t("k_field_edge_width"), self.edge_width_spinbox)
        
        content_layout.addWidget(edge_group)
        
        # ===== Toast通知设置 =====
        toast_group = QGroupBox(t("k_color_toast_style"))
        toast_layout = QFormLayout(toast_group)
        
        # Toast信息颜色
        self.toast_info_btn = QPushButton(t("k_color_select"))
        self.toast_info_btn.setStyleSheet(f"background-color: {colors['toast_info_color']}; min-height: 30px;")
        self.toast_info_btn.clicked.connect(lambda: self.choose_color('toast_info', colors['toast_info_color']))
        toast_layout.addRow(t("k_field_toast_info"), self.toast_info_btn)
        
        # Toast成功颜色
        self.toast_success_btn = QPushButton(t("k_color_select"))
        self.toast_success_btn.setStyleSheet(f"background-color: {colors['toast_success_color']}; min-height: 30px;")
        self.toast_success_btn.clicked.connect(lambda: self.choose_color('toast_success', colors['toast_success_color']))
        toast_layout.addRow(t("k_field_toast_success"), self.toast_success_btn)
        
        # Toast警告颜色
        self.toast_warning_btn = QPushButton(t("k_color_select"))
        self.toast_warning_btn.setStyleSheet(f"background-color: {colors['toast_warning_color']}; min-height: 30px;")
        self.toast_warning_btn.clicked.connect(lambda: self.choose_color('toast_warning', colors['toast_warning_color']))
        toast_layout.addRow(t("k_field_toast_warning"), self.toast_warning_btn)
        
        # Toast错误颜色
        self.toast_error_btn = QPushButton(t("k_color_select"))
        self.toast_error_btn.setStyleSheet(f"background-color: {colors['toast_error_color']}; min-height: 30px;")
        self.toast_error_btn.clicked.connect(lambda: self.choose_color('toast_error', colors['toast_error_color']))
        toast_layout.addRow(t("k_field_toast_error"), self.toast_error_btn)
        
        # Toast文字颜色
        self.toast_text_btn = QPushButton(t("k_color_select"))
        self.toast_text_btn.setStyleSheet(f"background-color: {colors['toast_text_color']}; min-height: 30px;")
        self.toast_text_btn.clicked.connect(lambda: self.choose_color('toast_text', colors['toast_text_color']))
        toast_layout.addRow(t("k_field_toast_text"), self.toast_text_btn)
        
        # Toast透明度
        self.toast_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.toast_opacity_slider.setRange(10, 100)
        self.toast_opacity_slider.setValue(int(colors['toast_opacity'] * 100))
        self.toast_opacity_slider.valueChanged.connect(self.update_toast_opacity_label)
        self.toast_opacity_label = QLabel(f"{int(colors['toast_opacity'] * 100)}%")
        toast_opacity_layout = QVBoxLayout()
        toast_opacity_layout.addWidget(self.toast_opacity_slider)
        toast_opacity_layout.addWidget(self.toast_opacity_label)
        toast_layout.addRow(t("k_field_toast_opacity"), toast_opacity_layout)
        
        content_layout.addWidget(toast_group)
        
        # ===== Dock 面板漂浮边框设置 =====
        dock_group = QGroupBox(t("k_color_dock_style"))
        dock_layout = QFormLayout(dock_group)
        
        self.dock_border_active_btn = QPushButton(t("k_color_select"))
        self.dock_border_active_btn.setStyleSheet(f"background-color: {colors['dock_floating_border_color']}; min-height: 30px;")
        self.dock_border_active_btn.clicked.connect(lambda: self.choose_color('dock_active', colors['dock_floating_border_color']))
        dock_layout.addRow(t("k_field_dock_active"), self.dock_border_active_btn)
        
        self.dock_border_inactive_btn = QPushButton(t("k_color_select"))
        self.dock_border_inactive_btn.setStyleSheet(f"background-color: {colors['dock_floating_border_inactive']}; min-height: 30px;")
        self.dock_border_inactive_btn.clicked.connect(lambda: self.choose_color('dock_inactive', colors['dock_floating_border_inactive']))
        dock_layout.addRow(t("k_field_dock_inactive"), self.dock_border_inactive_btn)
        
        content_layout.addWidget(dock_group)
        
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
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        content_layout.addLayout(button_layout)
        
    def _get_current_colors(self):
        """获取当前颜色值（从canvas或使用默认值）"""
        default_colors = {
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
            'edge_width': 2,
            'toast_info_color': '#323232',
            'toast_success_color': '#4caf50',
            'toast_warning_color': '#ff9800',
            'toast_error_color': '#f44336',
            'toast_text_color': '#ffffff',
            'toast_opacity': 0.9,
            'dock_floating_border_color': '#007acc',
            'dock_floating_border_inactive': '#3c3c3c'
        }
        
        canvas = self._get_canvas()
        if canvas:
            return {
                'canvas_bg_color': getattr(canvas, 'canvas_bg_color', default_colors['canvas_bg_color']),
                'grid_color': getattr(canvas, 'grid_color', default_colors['grid_color']),
                'grid_opacity': getattr(canvas, 'grid_opacity', default_colors['grid_opacity']),
                'node_bg_color': getattr(canvas, 'node_bg_color', default_colors['node_bg_color']),
                'node_border_color': getattr(canvas, 'node_border_color', default_colors['node_border_color']),
                'node_text_color': getattr(canvas, 'node_text_color', default_colors['node_text_color']),
                'node_selected_color': getattr(canvas, 'node_selected_color', default_colors['node_selected_color']),
                'input_anchor_color': getattr(canvas, 'input_anchor_color', default_colors['input_anchor_color']),
                'output_anchor_color': getattr(canvas, 'output_anchor_color', default_colors['output_anchor_color']),
                'edge_color': getattr(canvas, 'edge_color', default_colors['edge_color']),
                'edge_width': getattr(canvas, 'edge_width', default_colors['edge_width']),
                'toast_info_color': getattr(canvas, 'toast_info_color', default_colors['toast_info_color']),
                'toast_success_color': getattr(canvas, 'toast_success_color', default_colors['toast_success_color']),
                'toast_warning_color': getattr(canvas, 'toast_warning_color', default_colors['toast_warning_color']),
                'toast_error_color': getattr(canvas, 'toast_error_color', default_colors['toast_error_color']),
                'toast_text_color': getattr(canvas, 'toast_text_color', default_colors['toast_text_color']),
                'toast_opacity': getattr(canvas, 'toast_opacity', default_colors['toast_opacity']),
                'dock_floating_border_color': getattr(canvas, 'dock_floating_border_color', default_colors['dock_floating_border_color']),
                'dock_floating_border_inactive': getattr(canvas, 'dock_floating_border_inactive', default_colors['dock_floating_border_inactive'])
            }
        return default_colors

    def update_grid_opacity_label(self, value):
        """更新网格线透明度标签"""
        self.grid_opacity_label.setText(f"{value}%")
    
    def update_toast_opacity_label(self, value):
        """更新Toast透明度标签"""
        self.toast_opacity_label.setText(f"{value}%")
        
    def choose_color(self, target, default_color):
        """选择颜色 — target 需匹配 collect_settings 的字段名"""
        current_color = QColor(getattr(self, f'temp_{target}_color', default_color))
        new_color = QColorDialog.getColor(current_color, self, t("k_color_select"))
        
        if new_color.isValid():
            color_hex = new_color.name()
            
            btn_map = {
                'canvas_bg': self.canvas_color_btn,
                'grid': self.grid_color_btn,
                'node_bg': self.node_bg_btn,
                'node_border': self.node_border_btn,
                'node_text': self.node_text_btn,
                'node_selected': self.node_selected_btn,
                'input_anchor': self.input_anchor_btn,
                'output_anchor': self.output_anchor_btn,
                'edge': self.edge_color_btn,
                'toast_info': self.toast_info_btn,
                'toast_success': self.toast_success_btn,
                'toast_warning': self.toast_warning_btn,
                'toast_error': self.toast_error_btn,
                'toast_text': self.toast_text_btn,
                'dock_active': self.dock_border_active_btn,
                'dock_inactive': self.dock_border_inactive_btn
            }
            
            btn_map[target].setStyleSheet(f"background-color: {color_hex}; min-height: 30px;")
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
                'edge_width': 2,
                'dock_floating_border_color': '#007acc',
                'dock_floating_border_inactive': '#3c3c3c'
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
                'edge_width': 2,
                'dock_floating_border_color': '#007acc',
                'dock_floating_border_inactive': '#d4d4d4'
            }
        }
        
        theme = themes.get(theme_name)
        if theme:
            for key, value in theme.items():
                setattr(self, f'temp_{key}', value)
                
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
            self.dock_border_active_btn.setStyleSheet(f"background-color: {theme['dock_floating_border_color']}; min-height: 30px;")
            self.dock_border_inactive_btn.setStyleSheet(f"background-color: {theme['dock_floating_border_inactive']}; min-height: 30px;")
            
    def collect_settings(self):
        """收集当前所有颜色设置（供 apply 和 confirm 共用）"""
        colors = self._get_current_colors()
        return {
            'canvas_bg_color': getattr(self, 'temp_canvas_bg_color', colors['canvas_bg_color']),
            'grid_color': getattr(self, 'temp_grid_color', colors['grid_color']),
            'grid_opacity': self.grid_opacity_slider.value() / 100.0,
            'node_bg_color': getattr(self, 'temp_node_bg_color', colors['node_bg_color']),
            'node_border_color': getattr(self, 'temp_node_border_color', colors['node_border_color']),
            'node_text_color': getattr(self, 'temp_node_text_color', colors['node_text_color']),
            'node_selected_color': getattr(self, 'temp_node_selected_color', colors['node_selected_color']),
            'input_anchor_color': getattr(self, 'temp_input_anchor_color', colors['input_anchor_color']),
            'output_anchor_color': getattr(self, 'temp_output_anchor_color', colors['output_anchor_color']),
            'edge_color': getattr(self, 'temp_edge_color', colors['edge_color']),
            'edge_width': self.edge_width_spinbox.value(),
            'toast_info_color': getattr(self, 'temp_toast_info_color', colors['toast_info_color']),
            'toast_success_color': getattr(self, 'temp_toast_success_color', colors['toast_success_color']),
            'toast_warning_color': getattr(self, 'temp_toast_warning_color', colors['toast_warning_color']),
            'toast_error_color': getattr(self, 'temp_toast_error_color', colors['toast_error_color']),
            'toast_text_color': getattr(self, 'temp_toast_text_color', colors['toast_text_color']),
            'toast_opacity': self.toast_opacity_slider.value() / 100.0,
            'dock_floating_border_color': getattr(self, 'temp_dock_active_color', colors['dock_floating_border_color']),
            'dock_floating_border_inactive': getattr(self, 'temp_dock_inactive_color', colors['dock_floating_border_inactive'])
        }

    def apply_settings(self):
        """应用颜色设置（不关闭窗口）"""
        settings = self.collect_settings()
        canvas = self._get_canvas()
        if canvas:
            canvas.apply_color_settings(settings)
            canvas._save_color_settings()
        self._apply_global_settings(settings)
        themed_message(self, t("k_title_success"), t("k_color_applied"), "info")

    def _apply_global_settings(self, settings):
        """应用全局设置（当没有画布时）"""
        from ui.core.bnos_dock import set_dock_floating_colors as set_bnos_dock_colors
        from ui.core.dock_manager import set_dock_floating_colors as set_mgr_dock_colors
        from ui.core.toast.toast_notification import set_toast_config
        
        dock_active = settings.get('dock_floating_border_color', '#007acc')
        dock_inactive = settings.get('dock_floating_border_inactive', '#3c3c3c')
        set_bnos_dock_colors(dock_active, dock_inactive)
        set_mgr_dock_colors(dock_active, dock_inactive)
        
        set_toast_config({
            'info_color': settings.get('toast_info_color', '#323232'),
            'success_color': settings.get('toast_success_color', '#4caf50'),
            'warning_color': settings.get('toast_warning_color', '#ff9800'),
            'error_color': settings.get('toast_error_color', '#f44336'),
            'text_color': settings.get('toast_text_color', '#ffffff'),
            'opacity': settings.get('toast_opacity', 0.9),
        })

    def confirm_and_close(self):
        """确认并关闭：应用设置后关闭窗口"""
        settings = self.collect_settings()
        canvas = self._get_canvas()
        if canvas:
            canvas.apply_color_settings(settings)
            canvas._save_color_settings()
        self._apply_global_settings(settings)
        self.close()
            
    def reset_to_default(self):
        """恢复到默认颜色"""
        self.apply_preset_theme('dark')
        themed_message(self, t("k_title_info"), t("k_color_reset_done"), "info")
"""
节点样式抽象基类 — 只定义属性，不实现渲染
"""
from PyQt6.QtGui import QColor


class NodeStyle:
    """节点样式抽象基类 — 子类实现 apply() / apply_status()"""

    style_key: str = "abstract"
    style_name: str = "抽象"
    is_dot: bool = False

    # ===== 几何 =====
    node_width: int = 140
    node_height: int = 120

    # 状态显示相关
    status_show: bool = False
    status_cpu_y: int = -45
    status_mem_y: int = -30
    status_duration_x: int = -80
    status_duration_y: int = 10
    status_bar_height: int = 6

    # ===== 颜色 =====
    bg_color: str = "#2d2d30"
    border_color: str = "#454545"
    text_color: str = "#d4d4d4"
    selected_color: str = "#007acc"
    selected_border_width: int = 3
    lang_color: str = "#888888"

    status_stopped: str = "#888888"
    status_stopped_border: str = "#666666"
    status_idle: str = "#44FF44"
    status_idle_border: str = "#00CC00"
    status_running: str = "#FF4444"
    status_running_border: str = "#CC0000"

    cpu_text_color: str = "#4ecdc4"
    cpu_bar_color: str = "#4ecdc4"
    mem_text_color: str = "#ff6b6b"
    mem_bar_color: str = "#ff6b6b"
    duration_text_color: str = "#ffe66d"
    status_bar_bg: str = "#333333"
    status_bar_border: str = "#555555"

    # ===== 字体 =====
    name_font_family: str = "Arial"
    name_font_size: int = 10
    name_font_bold: bool = True
    lang_font_family: str = "Arial"
    lang_font_size: int = 8
    lang_font_bold: bool = False
    status_font_family: str = "Arial"
    status_font_size: int = 7
    status_font_bold: bool = True

    def apply(self, node_item):
        """子类必须实现 — 将样式属性渲染到 node_item 上"""
        raise NotImplementedError

    def apply_status(self, node_item, status):
        """子类必须实现 — 根据 status 更新指示灯颜色"""
        raise NotImplementedError

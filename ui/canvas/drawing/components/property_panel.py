"""
标注属性面板 — 选中图形时显示，支持实时修改属性
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QSpinBox,
    QLineEdit, QPushButton, QFrame, QGridLayout, QTextEdit,
)

from ui.canvas.drawing.styles import PRESETS, apply_preset
from ui.core.i18n import t


class ColorButton(QPushButton):
    """颜色选择按钮"""
    color_changed = Signal(str)

    def __init__(self, color="#00AAFF", parent=None):
        super().__init__(parent)
        self._color = color
        self.setFixedSize(24, 24)
        self._update_style()
        self.clicked.connect(self._pick_color)

    def _update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._color};
                border: 1px solid #666;
                border-radius: 4px;
            }}
            QPushButton:hover {{ border: 1px solid #FFF; }}
        """)

    def _pick_color(self):
        from PySide6.QtWidgets import QColorDialog
        c = QColorDialog.getColor(QColor(self._color), self)
        if c.isValid():
            self._color = c.name()
            self._update_style()
            self.color_changed.emit(self._color)

    def set_color(self, color: str):
        self._color = color
        self._update_style()


class DrawPropertyPanel(QWidget):
    """绘图属性面板"""

    def __init__(self, draw_layer, parent=None):
        super().__init__(parent)
        self.draw_layer = draw_layer
        self._updating = False  # 防止循环更新
        self._setup_ui()
        self._connect_signals()
        self.refresh()

    def _setup_ui(self):
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(200)
        self.setMaximumWidth(240)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 标题
        title = QLabel(t("属性"))
        title.setStyleSheet("font-weight: bold; color: #FFF; font-size: 13px;")
        layout.addWidget(title)

        # ── 预设样式 ──
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(4)
        self._preset_btns = {}
        for key, preset in PRESETS.items():
            btn = QPushButton()
            btn.setFixedSize(20, 20)
            btn.setToolTip(preset.name)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {preset.stroke_color};
                    border: 1px solid #555;
                    border-radius: 3px;
                }}
                QPushButton:hover {{ border: 1px solid #FFF; }}
            """)
            btn.clicked.connect(lambda checked, k=key: self._apply_preset(k))
            preset_layout.addWidget(btn)
            self._preset_btns[key] = btn
        preset_layout.addStretch()
        layout.addLayout(preset_layout)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("color: #444;")
        layout.addWidget(sep1)

        # ── 通用属性 ──
        grid = QGridLayout()
        grid.setColumnStretch(1, 1)
        grid.setSpacing(6)

        # 描边颜色
        grid.addWidget(QLabel(t("描边")), 0, 0)
        self.stroke_btn = ColorButton()
        grid.addWidget(self.stroke_btn, 0, 1, alignment=Qt.AlignmentFlag.AlignLeft)

        # 填充颜色
        grid.addWidget(QLabel(t("填充")), 1, 0)
        self.fill_btn = ColorButton()
        grid.addWidget(self.fill_btn, 1, 1, alignment=Qt.AlignmentFlag.AlignLeft)

        # 描边宽度
        grid.addWidget(QLabel(t("线宽")), 2, 0)
        self.stroke_w_slider = QSlider(Qt.Orientation.Horizontal)
        self.stroke_w_slider.setRange(1, 20)
        self.stroke_w_spin = QSpinBox()
        self.stroke_w_spin.setRange(1, 20)
        h = QHBoxLayout()
        h.addWidget(self.stroke_w_slider)
        h.addWidget(self.stroke_w_spin)
        grid.addLayout(h, 2, 1)

        # 不透明度
        grid.addWidget(QLabel(t("不透明度")), 3, 0)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setSuffix("%")
        h2 = QHBoxLayout()
        h2.addWidget(self.opacity_slider)
        h2.addWidget(self.opacity_spin)
        grid.addLayout(h2, 3, 1)

        layout.addLayout(grid)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #444;")
        layout.addWidget(sep2)

        # ── 文本属性（动态显示）──
        self.text_group = QWidget()
        text_layout = QGridLayout(self.text_group)
        text_layout.setSpacing(6)

        text_layout.addWidget(QLabel(t("文字")), 0, 0)
        self.text_edit = QLineEdit()
        text_layout.addWidget(self.text_edit, 0, 1)

        text_layout.addWidget(QLabel(t("字号")), 1, 0)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 72)
        text_layout.addWidget(self.font_size_spin, 1, 1)

        text_layout.addWidget(QLabel(t("文字色")), 2, 0)
        self.text_color_btn = ColorButton("#FFFFFF")
        text_layout.addWidget(self.text_color_btn, 2, 1, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(self.text_group)

        # ── 矩形属性（动态显示）──
        self.rect_group = QWidget()
        rect_layout = QGridLayout(self.rect_group)
        rect_layout.setSpacing(6)

        rect_layout.addWidget(QLabel(t("圆角")), 0, 0)
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(0, 50)
        self.radius_spin = QSpinBox()
        self.radius_spin.setRange(0, 50)
        h3 = QHBoxLayout()
        h3.addWidget(self.radius_slider)
        h3.addWidget(self.radius_spin)
        rect_layout.addLayout(h3, 0, 1)

        layout.addWidget(self.rect_group)

        # ── 箭头属性（动态显示）──
        self.arrow_group = QWidget()
        arrow_layout = QGridLayout(self.arrow_group)
        arrow_layout.setSpacing(6)

        arrow_layout.addWidget(QLabel(t("箭头大小")), 0, 0)
        self.arrow_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.arrow_size_slider.setRange(5, 50)
        self.arrow_size_spin = QSpinBox()
        self.arrow_size_spin.setRange(5, 50)
        h4 = QHBoxLayout()
        h4.addWidget(self.arrow_size_slider)
        h4.addWidget(self.arrow_size_spin)
        arrow_layout.addLayout(h4, 0, 1)

        layout.addWidget(self.arrow_group)

        layout.addStretch()

        # 样式
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(40, 40, 40, 0.95);
                color: #CCC;
                font-size: 12px;
            }
            QLabel { color: #AAA; }
            QLineEdit, QSpinBox {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 3px;
                color: #FFF;
                padding: 3px;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: #444;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 10px;
                height: 10px;
                background: #00AAFF;
                border-radius: 5px;
            }
        """)

    def _connect_signals(self):
        # 描边
        self.stroke_btn.color_changed.connect(lambda c: self._apply_style(stroke_color=c))
        # 填充
        self.fill_btn.color_changed.connect(lambda c: self._apply_style(fill_color=c))
        # 线宽
        self.stroke_w_slider.valueChanged.connect(self.stroke_w_spin.setValue)
        self.stroke_w_spin.valueChanged.connect(self.stroke_w_slider.setValue)
        self.stroke_w_spin.valueChanged.connect(lambda v: self._apply_style(stroke_w=v))
        # 不透明度
        self.opacity_slider.valueChanged.connect(self.opacity_spin.setValue)
        self.opacity_spin.valueChanged.connect(self.opacity_slider.setValue)
        self.opacity_spin.valueChanged.connect(self._apply_opacity)
        # 文本
        self.text_edit.editingFinished.connect(self._apply_text)
        self.font_size_spin.valueChanged.connect(lambda v: self._apply_style(font_size=v))
        self.text_color_btn.color_changed.connect(lambda c: self._apply_style(text_color=c))
        # 圆角
        self.radius_slider.valueChanged.connect(self.radius_spin.setValue)
        self.radius_spin.valueChanged.connect(self.radius_slider.setValue)
        self.radius_spin.valueChanged.connect(self._apply_radius)
        # 箭头
        self.arrow_size_slider.valueChanged.connect(self.arrow_size_spin.setValue)
        self.arrow_size_spin.valueChanged.connect(self.arrow_size_slider.setValue)
        self.arrow_size_spin.valueChanged.connect(self._apply_arrow_size)

    def refresh(self):
        """根据当前选中的图形刷新面板状态"""
        selected = self.draw_layer.selected_graphics()
        if not selected:
            self.hide()
            return

        self.show()
        self._updating = True

        # 判断是否有文本/矩形/箭头
        has_text = any(g.gtype == "text" for g in selected)
        has_rect = any(g.gtype in ("rect", "round_rect") for g in selected)
        has_arrow = any(g.gtype == "arrow" for g in selected)

        self.text_group.setVisible(has_text)
        self.rect_group.setVisible(has_rect)
        self.arrow_group.setVisible(has_arrow)

        # 取第一个图形的属性作为显示值（多选时不一致显示默认值）
        first = selected[0]
        style = first.to_dict().get("style", {})

        self.stroke_btn.set_color(style.get("stroke", "#00AAFF"))
        fill = style.get("fill")
        self.fill_btn.set_color(fill if fill else "transparent")
        self.stroke_w_spin.setValue(int(style.get("stroke_w", 2)))

        # 文本
        if has_text:
            text_g = next((g for g in selected if g.gtype == "text"), None)
            if text_g:
                self.text_edit.setText(text_g._text)
                self.font_size_spin.setValue(text_g._font.pointSize())
                self.text_color_btn.set_color(text_g._text_color.name())

        # 圆角
        if has_rect:
            rect_g = next((g for g in selected if g.gtype in ("rect", "round_rect")), None)
            if rect_g and hasattr(rect_g, "_rx"):
                self.radius_spin.setValue(int(rect_g._rx))

        # 箭头
        if has_arrow:
            arrow_g = next((g for g in selected if g.gtype == "arrow"), None)
            if arrow_g and hasattr(arrow_g, "_arrow_size"):
                self.arrow_size_spin.setValue(int(arrow_g._arrow_size))

        self._updating = False

    def _apply_style(self, **kwargs):
        if self._updating:
            return
        self.draw_layer._save_undo()
        for g in self.draw_layer.selected_graphics():
            g.set_style(**kwargs)
        self.draw_layer.canvas._save_timer.start(500)

    def _apply_opacity(self, value):
        if self._updating:
            return
        self.draw_layer._save_undo()
        for g in self.draw_layer.selected_graphics():
            g.setOpacity(value / 100.0)
        self.draw_layer.canvas._save_timer.start(500)

    def _apply_text(self):
        if self._updating:
            return
        text = self.text_edit.text()
        for g in self.draw_layer.selected_graphics():
            if g.gtype == "text" and hasattr(g, "set_text"):
                g.set_text(text)
        self.draw_layer.canvas._save_timer.start(500)

    def _apply_radius(self, value):
        if self._updating:
            return
        self.draw_layer._save_undo()
        for g in self.draw_layer.selected_graphics():
            if g.gtype in ("rect", "round_rect") and hasattr(g, "set_radius"):
                g.set_radius(value)
        self.draw_layer.canvas._save_timer.start(500)

    def _apply_arrow_size(self, value):
        if self._updating:
            return
        self.draw_layer._save_undo()
        for g in self.draw_layer.selected_graphics():
            if g.gtype == "arrow" and hasattr(g, "set_arrow_size"):
                g.set_arrow_size(value)
        self.draw_layer.canvas._save_timer.start(500)

    def _apply_preset(self, preset_key: str):
        self.draw_layer._save_undo()
        for g in self.draw_layer.selected_graphics():
            apply_preset(g, preset_key)
        self.refresh()
        self.draw_layer.canvas._save_timer.start(500)

"""
圆形节点样式 — 节点模式
"""
from PySide6.QtWidgets import QGraphicsEllipseItem
from PySide6.QtGui import QPen, QBrush, QFont, QColor
from PySide6.QtCore import Qt
from ._base import NodeStyle


class DotNodeStyle(NodeStyle):
    """节点模式 — 圆形 + 单锚点"""
    style_key: str = "dot"
    style_name: str = "k_node_style_circular"
    is_dot: bool = True

    node_width: int = 80
    node_height: int = 80
    dot_radius: int = 20
    name_font_size: int = 9
    lang_font_size: int = 7

    def apply(self, node_item):
        # —— 清理 panel 模式留下的 proxy widgets ——
        if hasattr(node_item, "_proxy_widgets") and node_item._proxy_widgets:
            for p in node_item._proxy_widgets:
                try:
                    p.setWidget(None)
                    if p.scene():
                        p.scene().removeItem(p)
                except Exception:
                    pass
            node_item._proxy_widgets.clear()
        if hasattr(node_item, "_param_row_positions"):
            node_item._param_row_positions.clear()

        w, h = self.node_width, self.node_height
        r = self.dot_radius
        cx, cy = w // 2 - r, h // 4 - r

        # 方框覆盖整个节点区域（圆点+文字），避免移动时网格残影
        node_item.prepareGeometryChange()
        node_item.setBrush(QBrush(Qt.GlobalColor.transparent))
        node_item.setPen(QPen(Qt.PenStyle.NoPen))
        node_item.setRect(0, 0, w, h)

        # 隐藏方框专属组件
        for attr in ('_in_label', '_out_label', '_expand_btn', '_expand_label'):
            if hasattr(node_item, attr) and getattr(node_item, attr, None):
                getattr(node_item, attr).setVisible(False)
        node_item.status_indicator.setVisible(False)
        node_item._expand_btn_rect.setRect(-100, -100, 1, 1)
        # 隐藏状态监控组件（CPU/MEM/Duration 条）
        if hasattr(node_item, "_status_widget") and node_item._status_widget:
            node_item._status_widget.set_visible(False)

        # 圆形节点：单锚点（不支持多输入，会重叠）
        out_sz = r * 2
        in_extra = 6
        in_sz = r * 2 + in_extra
        anchor_out_pos = (cx, cy)
        anchor_in_pos = (cx - in_extra // 2, cy - in_extra // 2)

        if hasattr(node_item, 'anchor_manager'):
            node_item.anchor_manager.layout_for_dot(
                w, h,
                anchor_in_size=in_sz, anchor_in_pos=anchor_in_pos,
                anchor_out_size=out_sz, anchor_out_pos=anchor_out_pos,
            )
        else:
            if hasattr(node_item, 'destroy_all_anchors'):
                node_item.destroy_all_anchors()
            if hasattr(node_item, '_ensure_default_anchors'):
                node_item._ensure_default_anchors()
            if hasattr(node_item, 'output_anchor') and node_item.output_anchor:
                node_item.output_anchor.setRect(0, 0, out_sz, out_sz)
                node_item.output_anchor.setPos(cx, cy)
                node_item.output_anchor.setZValue(4)
                node_item.output_anchor.setVisible(True)
                node_item.output_anchor.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            if hasattr(node_item, 'input_anchor') and node_item.input_anchor:
                node_item.input_anchor.setRect(0, 0, in_sz, in_sz)
                node_item.input_anchor.setPos(cx - in_extra // 2, cy - in_extra // 2)
                node_item.input_anchor.setZValue(5)
                node_item.input_anchor.setVisible(True)
                node_item.input_anchor.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        # 指示灯 — 最上层 (z=6)
        body_sz = r * 2
        if not hasattr(node_item, '_body') or node_item._body is None:
            node_item._body = QGraphicsEllipseItem(cx, cy, body_sz, body_sz, node_item)
        else:
            node_item._body.setRect(cx, cy, body_sz, body_sz)
        node_item._body.setZValue(6)
        node_item._body.setVisible(True)
        node_item._body.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        self.apply_status(node_item, node_item.status)

        # 文字
        dot_bottom = cy + 2 * r
        text_x = cx
        f = QFont(self.name_font_family, self.name_font_size)
        if self.name_font_bold:
            f.setBold(True)
        node_item.name_text.setDefaultTextColor(QColor(self.text_color))
        node_item.name_text.setFont(f)
        node_item.name_text.setVisible(True)
        node_item.name_text.setPos(text_x, dot_bottom + 2)

        f2 = QFont(self.lang_font_family, self.lang_font_size)
        if self.lang_font_bold:
            f2.setBold(True)
        node_item.lang_text.setDefaultTextColor(QColor(self.lang_color))
        node_item.lang_text.setFont(f2)
        node_item.lang_text.setVisible(True)
        nr = node_item.name_text.boundingRect()
        node_item.lang_text.setPos(text_x, dot_bottom + 2 + nr.height() + 1)

    def apply_status(self, node_item, status):
        if hasattr(node_item, '_body') and node_item._body:
            if status == "running":
                c, b = QColor(self.status_running), QColor(self.status_running_border)
            elif status == "idle":
                c, b = QColor(self.status_idle), QColor(self.status_idle_border)
            else:
                c, b = QColor(self.status_stopped), QColor(self.status_stopped_border)
            node_item._body.setBrush(QBrush(c))
            node_item._body.setPen(QPen(b, 2.5))

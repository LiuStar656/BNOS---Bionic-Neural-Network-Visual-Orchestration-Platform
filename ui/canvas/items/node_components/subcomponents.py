"""
节点子组件构造模块 — 集中管理文本标签、状态灯、展开按钮等子控件
"""
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPen, QFont
from PySide6.QtWidgets import (QGraphicsRectItem, QGraphicsTextItem,
                                 QGraphicsEllipseItem)


class NodeSubComponents:
    """子组件统一构造：文本标签、状态灯、展开按钮"""

    def __init__(self, node: QGraphicsRectItem):
        self._node = node

    def build_text_labels(self):
        """构造 IN/OUT 标签 + 名称 + 语言 文本项"""
        self._node._in_label = QGraphicsTextItem("IN", self._node)
        self._node._in_label.setZValue(4)
        self._node._out_label = QGraphicsTextItem("OUT", self._node)
        self._node._out_label.setZValue(4)
        self._node.name_text = QGraphicsTextItem(self._node.node_name, self._node)
        self._node.name_text.setZValue(4)
        self._node.lang_text = QGraphicsTextItem(self._node.language, self._node)
        self._node.lang_text.setZValue(4)

    def build_status_indicator(self):
        """构造状态灯（指示灯）"""
        self._node.status_indicator = QGraphicsEllipseItem(8, 8, 10, 10, self._node)
        self._node.status_indicator.setZValue(3)

    def build_expand_button(self):
        """构造展开按钮（视觉矩形 + 文本）"""
        self._node._expand_btn = QGraphicsRectItem(0, 0, 14, 14, self._node)
        self._node._expand_btn.setZValue(4)
        self._node._expand_btn_rect = QRectF(0, 0, 14, 14)
        self._node._expand_label = QGraphicsTextItem(">>", self._node)
        self._node._expand_label.setZValue(5)

    def build_selection_ring(self):
        """构造选中环（目前默认隐藏，面板模式下由 paint 直接绘制选中高亮）"""
        self._node._selection_ring = QGraphicsEllipseItem(self._node)
        self._node._selection_ring.setZValue(10)
        self._node._selection_ring.setVisible(False)

    def build_all(self):
        """按顺序构造全部子组件"""
        self.build_text_labels()
        self.build_status_indicator()
        self.build_expand_button()
        self.build_selection_ring()

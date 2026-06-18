"""
节点参数面板模块 — 详细参数面板构建/销毁、ProxyWidget 系统

从 node_item.py 拆分出来。这是最大的代码块（约 211 行），负责面板模式下
的参数控件容器构建、锚点位置缓存计算、文本/状态灯/语言标签布局。
"""
import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QGraphicsProxyWidget, QSizePolicy)
from ui.canvas.items.anchor_item import ANCHOR_SIZE, ANCHOR_SIZE_SMALL


class NodeParamPanel:
    """参数面板构建与销毁"""

    _ANCHOR_ZONE_WIDTH = 38
    _LEFT_INNER_PADDING = 8
    _RIGHT_INNER_PADDING = 8
    _ROW_SPACING = 6
    _ROW_HEIGHT = 32

    def __init__(self, node):
        self._node = node

    def build_detailed_view(self):
        """面板模式构建：主体显示参数控件，节点外显示名称/状态灯/语言标签

        关键点：
          - 使用 self._node._style（实例），而非 DetailedNodeStyle 类
          - 即使 config 为空或无参数，也必须设置节点尺寸 + 文本/状态灯/语言标签
          - 参数控件容器仅在有参数时构建
        """
        self._destroy_detailed()
        self._node._param_row_positions.clear()

        style = self._node._style

        # --- 读取 config（允许为空，空 config 也应正确渲染节点本体） ---
        config = self._node._config_manager.get_node_config()
        input_port_defs = []
        param_defs = []
        has_content = False
        if config:
            from ui.core.node_config_parser import NodeConfigParser, ParameterDef
            input_port_defs = NodeConfigParser.parse_input_ports(config) or []
            input_port_defs = [p for p in input_port_defs
                               if getattr(p, "source", "") == "node"]
            param_defs = NodeConfigParser.parse(config) or []
            has_content = bool(input_port_defs or param_defs)

        # --- 默认尺寸（无内容时也能显示节点本体） ---
        min_container_w = 340
        default_height = 80
        final_w = max(
            style.node_width if style and hasattr(style, "node_width") and style.node_width
            else min_container_w,
            min_container_w)
        final_h = default_height

        if has_content:
            # --- 有内容：构建参数控件容器 ---
            from ui.canvas.parameter_widgets import ParameterWidget

            container = QWidget()
            container.setStyleSheet("background: transparent;")

            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(
                self._ANCHOR_ZONE_WIDTH + self._LEFT_INNER_PADDING,
                6,
                self._RIGHT_INNER_PADDING,
                6,
            )
            v_layout.setSpacing(self._ROW_SPACING)

            row_types = []

            # 1) 输入端口行
            for port in input_port_defs:
                p_name = port.name
                label_text = getattr(port, "label", "") or port.name
                p_default = config.get(p_name, "") if p_name in config else ""
                param_obj = ParameterDef(
                    name=p_name, type="string", label=label_text, default=p_default)
                w = ParameterWidget.create(param_obj, p_default)
                if hasattr(w, "value_changed"):
                    w.value_changed.connect(self._node._config_manager.on_param_changed)
                w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                v_layout.addWidget(w)
                self._node._param_widgets[p_name] = w
                row_types.append("input_port")

            # 2) 参数行
            for p in param_defs:
                current = config.get(p.name, p.default)
                w = ParameterWidget.create(p, current)
                if hasattr(w, "value_changed"):
                    w.value_changed.connect(self._node._config_manager.on_param_changed)
                w.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                v_layout.addWidget(w)
                self._node._param_widgets[p.name] = w
                row_types.append("param")

            # 3) 输出行
            output_wrap = QWidget()
            output_wrap.setStyleSheet("background: transparent;")
            output_wrap.setMinimumHeight(self._ROW_HEIGHT)
            output_h_layout = QHBoxLayout(output_wrap)
            output_h_layout.setContentsMargins(0, 0, 0, 0)
            output_h_layout.addStretch(1)
            output_label = QLabel("output")
            out_font = QFont()
            out_font.setPointSize(9)
            output_label.setFont(out_font)
            output_label.setStyleSheet("color: #88ccff;")
            output_h_layout.addWidget(output_label)
            v_layout.addWidget(output_wrap)
            row_types.append("output")

            container.setMinimumWidth(min_container_w)
            container.layout().activate()
            sh = container.sizeHint()
            content_w = sh.width() if sh.isValid() else min_container_w
            content_h = sh.height() if sh.isValid() else (len(row_types) * 36 + 20)

            style.set_sizes(content_w, content_h)
            final_w = max(style.node_width, content_w)
            final_h = style.node_height
            self._node.setRect(0, 0, final_w, final_h)
            container.setFixedWidth(final_w)

            proxy = QGraphicsProxyWidget(self._node)
            proxy.setWidget(container)
            proxy.setPos(0, 0)
            proxy.setZValue(5)
            proxy.setFlag(proxy.GraphicsItemFlag.ItemClipsChildrenToShape, False)
            proxy.setFlag(proxy.GraphicsItemFlag.ItemClipsToShape, False)
            proxy.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self._node._proxy_widgets.append(proxy)

            # 计算锚点位置
            small_center_x = (self._ANCHOR_ZONE_WIDTH + self._LEFT_INNER_PADDING
                              - ANCHOR_SIZE_SMALL / 2 - 2)
            margins_top = v_layout.contentsMargins().top() if v_layout.contentsMargins() else 0
            running_y = 0
            est_ys = []
            for _j in range(len(row_types)):
                est_ys.append(running_y + self._ROW_HEIGHT / 2)
                running_y += self._ROW_HEIGHT + self._ROW_SPACING

            for i, rtype in enumerate(row_types):
                item = v_layout.itemAt(i) if v_layout else None
                geom = item.geometry() if item and item.widget() else None
                if geom is None or geom.width() <= 0 or geom.height() <= 0:
                    center_y = (
                        margins_top + est_ys[i] if i < len(est_ys)
                        else (margins_top + i * (self._ROW_HEIGHT + self._ROW_SPACING)
                              + self._ROW_HEIGHT / 2)
                    )
                else:
                    row_top = geom.y()
                    center_y = row_top + geom.height() / 2.0

                if rtype == "input_port":
                    port_idx = row_types[:i].count("input_port")
                    if port_idx < len(input_port_defs):
                        port = input_port_defs[port_idx]
                        self._node._param_row_positions[port.name] = (
                            small_center_x, center_y, ANCHOR_SIZE_SMALL,
                        )
                elif rtype == "output":
                    out_cx = final_w
                    out_cy = final_h / 2.0
                    self._node._param_row_positions["__output__"] = (
                        out_cx, out_cy, ANCHOR_SIZE)
        else:
            # 无参数：直接用默认尺寸
            self._node.setRect(0, 0, final_w, final_h)

        # --- 以下所有节点都必须执行：名称/状态灯/语言标签 ---
        # 节点名称：UI外上方
        title_font = QFont()
        title_font.setPointSize(10)
        title_font.setBold(True)
        self._node.name_text.setFont(title_font)
        self._node.name_text.setDefaultTextColor(QColor(style.header_text_color))
        self._node.name_text.setZValue(6)
        self._node.name_text.setPlainText(self._node.node_name)
        text_rect = self._node.name_text.boundingRect()
        title_x = max(4.0, (final_w - text_rect.width()) / 2)
        title_y = -text_rect.height()
        self._node.name_text.setPos(title_x, title_y)
        self._node.name_text.setVisible(True)

        # 状态指示灯（右上角，UI内）
        indicator_size = 10
        indicator_x = final_w - indicator_size - 8
        indicator_y = 4
        self._node.status_indicator.setRect(
            indicator_x, indicator_y, indicator_size, indicator_size)
        self._node.status_indicator.setZValue(7)
        self._node.status_indicator.setVisible(True)
        style.apply_status(self._node, self._node.status)

        # 语言标签：UI外底部居中
        lang_font = QFont()
        lang_font.setPointSize(8)
        self._node.lang_text.setFont(lang_font)
        self._node.lang_text.setDefaultTextColor(QColor("#888888"))
        self._node.lang_text.setZValue(6)
        self._node.lang_text.setPlainText(self._node.language)
        lr = self._node.lang_text.boundingRect()
        lang_x = (final_w - lr.width()) / 2
        lang_y = final_h + 2
        self._node.lang_text.setPos(lang_x, lang_y)
        self._node.lang_text.setVisible(True)

        # CPU/MEM 文本：与语言标签在同一水平线，靠左对齐
        if self._node._status_widget:
            self._node._status_widget.set_bottom_y(lang_y)

        self._node._config_manager.subscribe_config_changes()

    def _destroy_detailed(self):
        """销毁详细版控件（样式切换时调用），恢复缓存模式和默认尺寸"""
        for p in self._node._proxy_widgets:
            w = p.widget()
            if w:
                w.deleteLater()
            p.setWidget(None)
            if self._node.scene():
                self._node.scene().removeItem(p)
        self._node._proxy_widgets.clear()
        self._node._param_widgets.clear()
        # 先禁用缓存再重置 rect
        self._node.setCacheMode(self._node.CacheMode.NoCache)
        self._node.setRect(0, 0, self._node._style.node_width, self._node._style.node_height)
        self._node.setCacheMode(self._node.CacheMode.DeviceCoordinateCache)
        self._node.update()

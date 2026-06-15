"""
锚点对接系统 —— AnchorManager

设计思路：
- 锚点是一等公民，统一由 AnchorManager 管理，节点 / 样式 / 画布不再直接操作 AnchorItem
- 节点（NodeItem）持有一个 AnchorManager 实例
- 样式（NodeStyle）调用 AnchorManager 的 API，不直接 setRect / setPos
- 连线（EdgeItem / CanvasConnections）通过 AnchorManager 获取端点锚点
- 点击检测（CanvasView / NodeItem.mousePressEvent）统一走 find_nearest_xxx()

核心对象：
    NodeItem
     └── self.anchor_manager: AnchorManager
              ├── input_anchors:  dict[str, AnchorItem]
              ├── output_anchors: dict[str, AnchorItem]
              ├── input_labels:   dict[str, QGraphicsTextItem]
              └── output_labels:  dict[str, QGraphicsTextItem]

向后兼容：
    node.input_anchor  →  @property 锚点容器返回 anchor_manager.get_default_input()
    node.output_anchor →  @property 锚点容器返回 anchor_manager.get_default_output()
    所有旧代码（hasattr(node, 'input_anchor')）继续工作。
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsTextItem

from ui.canvas.items.anchor_item import (
    AnchorItem, ANCHOR_SIZE, ANCHOR_HALF,
    ANCHOR_SIZE_SMALL, ANCHOR_HALF_SMALL,
)
from ui.core.logger import logger


# ---------------------------------------------------------------------------
# 数据来源（端口模式）
# ---------------------------------------------------------------------------
class PortSource:
    """端口数据来源枚举——控制该端口是否在画布上生成锚点"""

    NODE = "node"      # 需要从上游节点连入数据 → 生成锚点
    EDIT = "edit"      # 用户手动输入（文本框 / 参数面板） → 不生成锚点
    PARAM = "param"    # 可选参数（文本框 / 下拉框，有 default） → 不生成锚点
    FILE = "file"      # 外部文件（预留扩展）→ 不生成锚点

    @classmethod
    def needs_anchor(cls, source: str | None) -> bool:
        """返回该数据来源是否需要生成画布锚点"""
        return source == cls.NODE


# ---------------------------------------------------------------------------
# AnchorManager —— 统一管理节点上所有输入/输出锚点
# ---------------------------------------------------------------------------
class AnchorManager:
    """节点锚点管理系统（对外唯一入口）"""

    # 最大点击距离（像素）——在此范围内才认为点击命中了某个锚点
    CLICK_TOLERANCE = 20

    def __init__(self, node_item):
        """
        参数:
            node_item: NodeItem —— 持有本管理器的节点图形项
        """
        self.node = node_item

        # 核心容器：端口名 → 锚点 / 标签
        self.input_anchors: dict[str, AnchorItem] = {}
        self.output_anchors: dict[str, AnchorItem] = {}
        self.input_labels: dict[str, QGraphicsTextItem] = {}
        self.output_labels: dict[str, QGraphicsTextItem] = {}

        # 初始化 default 锚点（保证旧代码零修改即可工作）
        self.ensure_default_anchors()

    # =============================================================
    # 生命周期：默认锚点 / 销毁
    # =============================================================

    def ensure_default_anchors(self) -> None:
        """确保一对 'default' 锚点存在。已存在则复用。"""
        if "default" not in self.input_anchors:
            anchor = self._make_anchor(
                anchor_type="input",
                port_name="default",
                port_type="default",
                port_label="",
            )
            self.input_anchors["default"] = anchor

        if "default" not in self.output_anchors:
            anchor = self._make_anchor(
                anchor_type="output",
                port_name="default",
                port_type="default",
                port_label="",
            )
            self.output_anchors["default"] = anchor

    def destroy_all(self) -> None:
        """销毁所有锚点与标签。通常在样式切换 / 重建时调用。"""
        self._remove_container(self.input_anchors)
        self._remove_container(self.output_anchors)
        self._remove_container(self.input_labels)
        self._remove_container(self.output_labels)

    # =============================================================
    # 根据 config.json 动态构建（多锚点系统核心）
    # =============================================================

    def build_from_config(self, config: Optional[dict],
                          row_positions: Optional[dict[str, tuple[float, float, int]]] = None,
                          node_w: float = 0, node_h: float = 0) -> None:
        """ComfyUI 风格：从 config.json 动态生成锚点布局。

        锚点生成规则（由 config.json 字段驱动，不再硬编码）：
          - 主输入锚点：仅当 config 中存在 listen_upper_file 字段时才生成，16px，
            位置优先取 row_positions["__listen_upper_file__"]，否则节点内部左上角（与状态灯对称）
          - 附加输入锚点：每个 input_ports 中 source=node 的端口，10px，贴在标签右边
          - 主输出锚点：仅当 config 中存在 output_file 字段时才生成，16px，
            位置优先取 row_positions["__output__"]，否则节点右下角

        row_positions 格式：{port_name: (anchor_center_x, anchor_center_y, size)}
          - anchor_center_x: 锚点中心 x（节点坐标系）
          - anchor_center_y: 锚点中心 y（节点坐标系）
          - size: 锚点尺寸（16=大锚点，10=小锚点）
        """
        # ================================================================
        # —— 1. 在销毁之前收集旧锚点上的 edges（关键：必须在 clear_edges 之前）——
        #     因为 _remove_container 会调用 anchor.clear_edges()，如果先销毁再收集，
        #     拿到的 edges_snapshot 永远是空的，导致重启后边缘绑定到已销毁的旧锚点。
        # ================================================================
        old_input_edges: list[tuple[str, list]] = []
        old_output_edges: list[tuple[str, list]] = []
        for name, a in list(self.input_anchors.items()):
            edges_snapshot = list(a.edges) if hasattr(a, "edges") else []
            if edges_snapshot:
                old_input_edges.append((name, edges_snapshot))
        for name, a in list(self.output_anchors.items()):
            edges_snapshot = list(a.edges) if hasattr(a, "edges") else []
            if edges_snapshot:
                old_output_edges.append((name, edges_snapshot))

        # —— 1b. 额外保险：从画布（节点所在画布）上扫描所有 edge，收集挂在本节点锚点上但
        #      anchor.edges 因各种原因已被清空的 edge（防止迁移遗漏）。
        canvas_edges_extra: list[tuple[str, str, object]] = []  # (kind, port_name, edge)
        node = self.node
        if node is not None and hasattr(node, "canvas") and node.canvas is not None:
            for edge in getattr(node.canvas, "edges", []) or []:
                # 输入端 edge
                if hasattr(edge, "end_anchor") and edge.end_anchor is not None:
                    ea = edge.end_anchor
                    if getattr(ea, "parentItem", None) is node and hasattr(ea, "port_name"):
                        pn = ea.port_name
                        # 只有在旧字典里能找到的 port_name 才加入兜底；
                        # 没在旧字典里的（例如 __output__/default）按锚点对象归属
                        if pn in self.input_anchors or (
                            hasattr(ea, "anchor_type") and ea.anchor_type == "input"
                        ):
                            canvas_edges_extra.append(("input", pn, edge))
                # 输出端 edge
                if hasattr(edge, "start_anchor") and edge.start_anchor is not None:
                    sa = edge.start_anchor
                    if getattr(sa, "parentItem", None) is node and hasattr(sa, "port_name"):
                        pn = sa.port_name
                        if pn in self.output_anchors or (
                            hasattr(sa, "anchor_type") and sa.anchor_type == "output"
                        ):
                            canvas_edges_extra.append(("output", pn, edge))

        # —— 2. 销毁旧锚点 ——
        self._remove_container(self.input_anchors)
        self._remove_container(self.output_anchors)
        self._remove_container(self.input_labels)
        self._remove_container(self.output_labels)

        # —— 3. 读取位置信息 ——
        positions = row_positions if row_positions is not None else getattr(
            self.node, "_param_row_positions", {})
        nw = node_w or (self.node.rect().width() if hasattr(self.node, "rect") else 0)
        nh = node_h or (self.node.rect().height() if hasattr(self.node, "rect") else 0)

        # —— 4. 解析 config 的 input_ports 信息 ——
        config_ports = {}
        try:
            from ui.core.node_config_parser import NodeConfigParser
            if config:
                for p in NodeConfigParser.parse_input_ports(config):
                    config_ports[p.name] = p
        except Exception:
            pass

        # —— 5. 生成主输入锚点（根据 config.json 中 listen_upper_file 字段动态决定）——
        # 仅当 config 中存在 listen_upper_file 字段时才生成，标签使用 config 中的实际值
        # 位置：节点左侧边线中点上（x=0, y=h/2）
        has_listen_upper = config and "listen_upper_file" in config
        if has_listen_upper:
            # 优先使用 __listen_upper_file__ 行位置，否则回退到左侧边线中点
            if "__listen_upper_file__" in positions:
                pos_tuple = positions["__listen_upper_file__"]
                if len(pos_tuple) >= 3:
                    main_center_x, main_center_y, main_size = pos_tuple
                elif len(pos_tuple) == 2:
                    main_center_y, _ = pos_tuple
                    main_center_x = 0.0
                    main_size = ANCHOR_SIZE
                else:
                    main_center_x = 0.0
                    main_center_y = nh / 2.0 if nh > 0 else ANCHOR_HALF
                    main_size = ANCHOR_SIZE
            else:
                main_center_x = 0.0
                main_center_y = nh / 2.0 if nh > 0 else ANCHOR_HALF
                main_size = ANCHOR_SIZE
            listen_label = config.get("listen_upper_file", "") or "listen_upper_file"
            main_anchor = self._make_anchor(
                anchor_type="input",
                port_name="default",
                port_type="default",
                port_label=listen_label,
                size=main_size,
            )
            main_anchor.setPos(main_center_x, main_center_y)
            main_anchor.setZValue(10)
            main_anchor.setVisible(True)
            self.input_anchors["default"] = main_anchor

        # —— 6. 生成其他输入锚点（input_ports 中的端口）——
        # 小锚点（10px），贴在各自行的标签右边
        for name, pos_tuple in positions.items():
            if name in ("__output__", "__listen_upper_file__", "__default__"):
                continue
            if len(pos_tuple) >= 3:
                center_x, center_y, size = pos_tuple
            elif len(pos_tuple) == 2:
                # 旧格式：(center_y, row_h) —— 回退到左边界
                center_y, _ = pos_tuple
                center_x = 0.0
                size = ANCHOR_SIZE_SMALL
            else:
                continue
            anchor = self._make_anchor(
                anchor_type="input",
                port_name=name,
                port_type=getattr(config_ports.get(name), "type", "string") if config_ports.get(name) else "string",
                port_label=name,
                size=size,
            )
            anchor.setPos(center_x, center_y)
            anchor.setZValue(10)
            anchor.setVisible(True)
            self.input_anchors[name] = anchor

        # —— 7. 生成主输出锚点（根据 config.json 中 output_file 字段动态决定）——
        # 仅当 config 中存在 output_file 字段时才生成，标签使用 config 中的实际值
        # 位置：节点右侧边线中点上（x=nw, y=nh/2）
        has_output_file = config and "output_file" in config
        if has_output_file:
            if "__output__" in positions:
                pos_tuple = positions["__output__"]
                if len(pos_tuple) >= 3:
                    out_center_x, out_center_y, out_size = pos_tuple
                elif len(pos_tuple) == 2:
                    out_center_y, _ = pos_tuple
                    out_center_x = nw
                    out_size = ANCHOR_SIZE
                else:
                    out_center_x = nw
                    out_center_y = nh / 2.0 if nh > 0 else ANCHOR_HALF
                    out_size = ANCHOR_SIZE
            else:
                out_center_x = nw
                out_center_y = nh / 2.0 if nh > 0 else ANCHOR_HALF
                out_size = ANCHOR_SIZE
            output_label = config.get("output_file", "") or "output_file"
            out_anchor = self._make_anchor(
                anchor_type="output",
                port_name="default",
                port_type="output",
                port_label=output_label,
                size=out_size,
            )
            out_anchor.setPos(out_center_x, out_center_y)
            out_anchor.setZValue(10)
            out_anchor.setVisible(True)
            self.output_anchors["default"] = out_anchor

        # —— 8. 迁移 edges（把旧锚点的 edge 绑定到新锚点，保持连线路径）——
        # 规则：优先使用 EdgeItem 自带的 _desired_target_port_name（连接时记录的原始端口名），
        #       其次用旧锚点的 port_name，都找不到用 default 锚点兜底
        migrated_edge_ids: set[int] = set()
        for _port_name, edges in old_input_edges:
            for edge in edges:
                try:
                    # 优先用 edge 自带的期望端口名（样式切换时不会丢失）
                    desired_port = getattr(edge, '_desired_target_port_name', None)
                    new_anchor = self.input_anchors.get(desired_port) if desired_port else None
                    if new_anchor is None:
                        new_anchor = self.input_anchors.get(_port_name)
                    if new_anchor is None:
                        new_anchor = self.input_anchors.get("default")
                    if new_anchor is None:
                        new_anchor = next(iter(self.input_anchors.values()), None)
                    if new_anchor is None:
                        continue
                    edge.end_anchor = new_anchor
                    new_anchor.add_edge(edge)
                    edge.update_path()
                    migrated_edge_ids.add(id(edge))
                except Exception:
                    pass

        # 输出端
        for _, edges in old_output_edges:
            for edge in edges:
                try:
                    desired_port = getattr(edge, '_desired_source_port_name', None)
                    new_anchor = self.output_anchors.get(desired_port) if desired_port else None
                    if new_anchor is None:
                        new_anchor = self.output_anchors.get("default")
                    if new_anchor is None:
                        new_anchor = next(iter(self.output_anchors.values()), None)
                    if new_anchor is None:
                        continue
                    edge.start_anchor = new_anchor
                    new_anchor.add_edge(edge)
                    edge.update_path()
                    migrated_edge_ids.add(id(edge))
                except Exception:
                    pass

        # —— 8b. 兜底：从 canvas.edges 扫描到的 edge 兜底迁移 ——
        for kind, port_name, edge in canvas_edges_extra:
            if id(edge) in migrated_edge_ids:
                continue
            try:
                if kind == "input":
                    # 优先用 edge 自带的期望端口名
                    desired_port = getattr(edge, '_desired_target_port_name', None)
                    new_anchor = (self.input_anchors.get(desired_port) if desired_port else None) \
                                 or self.input_anchors.get(port_name) \
                                 or self.input_anchors.get("default") \
                                 or (next(iter(self.input_anchors.values())) if self.input_anchors else None)
                    if new_anchor is None:
                        continue
                    edge.end_anchor = new_anchor
                    new_anchor.add_edge(edge)
                    edge.update_path()
                else:
                    desired_port = getattr(edge, '_desired_source_port_name', None)
                    new_anchor = (self.output_anchors.get(desired_port) if desired_port else None) \
                                 or self.output_anchors.get("default") \
                                 or (next(iter(self.output_anchors.values())) if self.output_anchors else None)
                    if new_anchor is None:
                        continue
                    edge.start_anchor = new_anchor
                    new_anchor.add_edge(edge)
                    edge.update_path()
            except Exception:
                pass


    # =============================================================
    # 对外查询 API（样式 / 点击检测 / 连线绑定都走这里）
    # =============================================================

    def get_input(self, port_name: str | None = None) -> Optional[AnchorItem]:
        """获取指定输入锚点；None → 返回 default。找不到返回 None。"""
        if port_name is None or port_name == "default":
            if "default" in self.input_anchors:
                return self.input_anchors["default"]
            # 兜底：返回第一个存在的锚点
            return next(iter(self.input_anchors.values())) if self.input_anchors else None
        return self.input_anchors.get(port_name)

    def get_output(self, port_name: str | None = None) -> Optional[AnchorItem]:
        """获取指定输出锚点；None → 返回 default。找不到返回 None。"""
        if port_name is None or port_name == "default":
            if "default" in self.output_anchors:
                return self.output_anchors["default"]
            return next(iter(self.output_anchors.values())) if self.output_anchors else None
        return self.output_anchors.get(port_name)

    # -- 兼容别名（旧代码通过 @property node.input_anchor / output_anchor 调用） --
    def get_default_input(self) -> Optional[AnchorItem]:
        return self.get_input(None)

    def get_default_output(self) -> Optional[AnchorItem]:
        return self.get_output(None)

    # -- 遍历接口 --
    def all_input(self) -> list[AnchorItem]:
        return list(self.input_anchors.values())

    def all_output(self) -> list[AnchorItem]:
        return list(self.output_anchors.values())

    # =============================================================
    # 点击检测：给定节点坐标系内的点击点，返回最近的锚点
    # =============================================================

    def find_nearest_input(self, pos_in_item: QPointF,
                            max_dist: int = CLICK_TOLERANCE) -> Optional[AnchorItem]:
        return self._find_nearest(pos_in_item, self.input_anchors, max_dist)

    def find_nearest_output(self, pos_in_item: QPointF,
                             max_dist: int = CLICK_TOLERANCE) -> Optional[AnchorItem]:
        return self._find_nearest(pos_in_item, self.output_anchors, max_dist)

    # =============================================================
    # 布局：方框模式 / 圆点模式 / 面板模式的锚点位置计算
    # =============================================================

    def layout_for_rect(self, w: float, h: float) -> None:
        """方框 / 圆点模式：左右各一个 default 锚点，水平居中。"""
        # 销毁非 default 锚点（方框模式不支持多锚点）
        self._keep_only_default()

        if "default" in self.input_anchors:
            anchor = self.input_anchors["default"]
            anchor.setRect(0, 0, ANCHOR_SIZE, ANCHOR_SIZE)
            anchor.setPos(-ANCHOR_HALF, h / 2 - ANCHOR_HALF)
            anchor.setZValue(1)
            anchor.setVisible(True)

        if "default" in self.output_anchors:
            anchor = self.output_anchors["default"]
            anchor.setRect(0, 0, ANCHOR_SIZE, ANCHOR_SIZE)
            anchor.setPos(w - ANCHOR_HALF, h / 2 - ANCHOR_HALF)
            anchor.setZValue(1)
            anchor.setVisible(True)

    def layout_for_dot(self, w: float, h: float,
                        anchor_in_size: float, anchor_in_pos: tuple[float, float],
                        anchor_out_size: float, anchor_out_pos: tuple[float, float]) -> None:
        """圆点模式：输入/输出锚点都覆盖圆点中心（尺寸更大便于点击）。"""
        self._keep_only_default()

        if "default" in self.input_anchors:
            anchor = self.input_anchors["default"]
            anchor.setRect(0, 0, anchor_in_size, anchor_in_size)
            anchor.setPos(*anchor_in_pos)
            anchor.setZValue(5)
            anchor.setVisible(True)
            anchor.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        if "default" in self.output_anchors:
            anchor = self.output_anchors["default"]
            anchor.setRect(0, 0, anchor_out_size, anchor_out_size)
            anchor.setPos(*anchor_out_pos)
            anchor.setZValue(4)
            anchor.setVisible(True)
            anchor.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    # =============================================================
    # 内部辅助
    # =============================================================

    def _make_anchor(self, *, anchor_type: str, port_name: str,
                     port_type: str, port_label: str,
                     size: int = ANCHOR_SIZE) -> AnchorItem:
        """工厂方法：创建一个 AnchorItem 并挂到节点下。

        参数：
            size: 锚点直径（像素）。主锚点 16px，小锚点 10px。
        """
        anchor = AnchorItem(
            -size / 2, -size / 2,  # 初始位置（相对于 anchor 自身；setPos 会覆盖）
            anchor_type=anchor_type,
            parent=self.node,
            port_name=port_name,
            port_type=port_type,
            port_label=port_label,
            size=size,
        )
        anchor.setZValue(10)
        return anchor

    def _remove_container(self, container: dict) -> None:
        """销毁字典中所有 Qt item，并清空字典。"""
        for item in list(container.values()):
            try:
                if hasattr(item, "clear_edges"):
                    item.clear_edges()
                scene = item.scene()
                if scene is not None:
                    scene.removeItem(item)
            except Exception:
                pass
        container.clear()

    def _keep_only_default(self) -> None:
        """只保留 'default' 锚点，删除其他多端口锚点（用于单锚点样式）。
        关键：被删除锚点上的 edges 会迁移到 default 锚点上，并更新 EdgeItem 的引用。
        """
        # —— 输入端：非 default 锚点的 edges 迁移到 default 输入锚点 ——
        default_in = self.input_anchors.get("default")
        for name in list(self.input_anchors.keys()):
            if name == "default":
                continue
            try:
                item = self.input_anchors.pop(name)
                # 把该锚点上的 edges 迁移到 default 锚点
                if hasattr(item, "edges") and item.edges and default_in is not None:
                    for edge in list(item.edges):
                        try:
                            edge.end_anchor = default_in
                            default_in.add_edge(edge)
                            edge.update_path()
                        except Exception:
                            pass
                if hasattr(item, "clear_edges"):
                    item.clear_edges()
                if item.scene() is not None:
                    item.scene().removeItem(item)
            except Exception:
                pass

        # —— 输出端：非 default 锚点的 edges 迁移到 default 输出锚点 ——
        default_out = self.output_anchors.get("default")
        for name in list(self.output_anchors.keys()):
            if name == "default":
                continue
            try:
                item = self.output_anchors.pop(name)
                if hasattr(item, "edges") and item.edges and default_out is not None:
                    for edge in list(item.edges):
                        try:
                            edge.start_anchor = default_out
                            default_out.add_edge(edge)
                            edge.update_path()
                        except Exception:
                            pass
                if hasattr(item, "clear_edges"):
                    item.clear_edges()
                if item.scene() is not None:
                    item.scene().removeItem(item)
            except Exception:
                pass

        # —— 清理 labels ——
        for name in list(self.input_labels.keys()):
            if name != "default":
                try:
                    item = self.input_labels.pop(name)
                    if item.scene() is not None:
                        item.scene().removeItem(item)
                except Exception:
                    pass
        for name in list(self.output_labels.keys()):
            if name != "default":
                try:
                    item = self.output_labels.pop(name)
                    if item.scene() is not None:
                        item.scene().removeItem(item)
                except Exception:
                    pass

    def _layout_anchors(self, *, ports: list, anchor_type: str,
                         node_w: float, node_h: float,
                         anchor_container: dict, label_container: dict) -> None:
        """通用：把一组端口沿左侧或右侧垂直均匀分布。"""
        if not ports:
            return

        header_h = 26  # 标题栏高度（与 node_style HEADER_HEIGHT 保持一致）
        divider = 4
        top = header_h + divider
        available_h = node_h - top - 16  # 上下各留 8px 边距
        n = len(ports)

        for i, port in enumerate(ports):
            # 计算锚点中心 y 坐标
            if n == 1:
                center_y = top + available_h / 2
            else:
                center_y = top + (available_h * i) / (n - 1)

            # 锚点 rect 左上角 = (中心 - ANCHOR_HALF)
            anchor_y = center_y - ANCHOR_HALF

            # 锚点水平位置（左侧/右侧）
            if anchor_type == "input":
                anchor_x = -ANCHOR_HALF  # 贴节点左边（左半延伸到节点外）
            else:
                anchor_x = node_w - ANCHOR_HALF  # 贴节点右边

            # 创建锚点
            anchor = self._make_anchor(
                anchor_type=anchor_type,
                port_name=port.name,
                port_type=getattr(port, "type", "default"),
                port_label=getattr(port, "label", "") or port.name,
            )
            anchor.setPos(anchor_x, anchor_y)
            anchor_container[port.name] = anchor

            # 创建标签（输入锚点在右侧显示，输出锚点在左侧显示，避免与线条重叠）
            label_text = getattr(port, "label", "") or port.name
            label = QGraphicsTextItem(label_text, self.node)
            label.setDefaultTextColor(QColor("#888"))
            label.setFont(self._get_label_font())
            label.setZValue(9)

            if anchor_type == "input":
                # 标签在锚点右边（节点内）
                label.setPos(ANCHOR_HALF + 6, center_y - 8)
            else:
                # 标签在锚点左边（节点内，右对齐）
                fm = label.document().idealWidth()
                label.setPos(node_w - ANCHOR_HALF - 6 - fm, center_y - 8)
            label_container[port.name] = label

    def _layout_default_input(self, w: float, h: float) -> None:
        if "default" in self.input_anchors:
            anchor = self.input_anchors["default"]
            anchor.setRect(0, 0, ANCHOR_SIZE, ANCHOR_SIZE)
            anchor.setPos(-ANCHOR_HALF, h / 2 - ANCHOR_HALF)
            anchor.setZValue(1)
            anchor.setVisible(True)

    def _layout_default_output(self, w: float, h: float) -> None:
        if "default" in self.output_anchors:
            anchor = self.output_anchors["default"]
            anchor.setRect(0, 0, ANCHOR_SIZE, ANCHOR_SIZE)
            anchor.setPos(w - ANCHOR_HALF, h / 2 - ANCHOR_HALF)
            anchor.setZValue(1)
            anchor.setVisible(True)

    def _find_nearest(self, pos: QPointF, container: dict,
                       max_dist: int) -> Optional[AnchorItem]:
        if not container:
            return None
        best = None
        best_dist = float("inf")
        for anchor in container.values():
            # pos() 直接返回锚点中心（_make_anchor 创建的 rect 本地中心在 (0,0)）
            center_x = anchor.pos().x()
            center_y = anchor.pos().y()
            dx = pos.x() - center_x
            dy = pos.y() - center_y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = anchor
        if best is not None and best_dist <= max_dist:
            return best
        return None

    @staticmethod
    def _get_label_font():
        """端口标签字体（与 NodeItem 现有字体保持一致）。"""
        from PySide6.QtGui import QFont
        f = QFont()
        f.setPointSize(8)
        f.setWeight(QFont.Weight.Light)
        return f

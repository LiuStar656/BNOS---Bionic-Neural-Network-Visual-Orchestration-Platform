"""
画布布局持久化 Mixin — 从 canvas_view.py 提取
save_layout / load_layout
"""
import os
import json
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QPen, QBrush, QColor
from PyQt6.QtWidgets import QGraphicsScene
from ui.canvas.items.node_item import NodeItem
from ui.canvas.items.edge_item import EdgeItem
from ui.core.logger import logger


class CanvasLayoutMixin:
    """布局保存/加载 Mixin"""

    def save_layout(self, project_path):
        if not project_path:
            return

        viewport_center = self.viewport().rect().center()
        center_scene_pos = self.mapToScene(viewport_center)

        layout_data = {
            "nodes": {},
            "edges": [],
            "view_state": {
                "scale": self.transform().m11(),
                "scroll_x": self.horizontalScrollBar().value(),
                "scroll_y": self.verticalScrollBar().value(),
                "center_x": center_scene_pos.x(),
                "center_y": center_scene_pos.y(),
            },
            "canvas_size": {
                "width": self.canvas_width,
                "height": self.canvas_height,
            },
        }

        for node_name, node in self.nodes.items():
            pos = node.pos()
            custom_colors = {}
            if self.parent_window and node_name in self.parent_window.nodes_data:
                config = self.parent_window.nodes_data[node_name].get("config", {})
                if "custom_bg_color" in config:
                    custom_colors["bg"] = config["custom_bg_color"]
                if "custom_border_color" in config:
                    custom_colors["border"] = config["custom_border_color"]
                if "custom_text_color" in config:
                    custom_colors["text"] = config["custom_text_color"]

            style_key = "rect"
            if hasattr(node, '_style') and hasattr(node._style, 'style_key'):
                style_key = node._style.style_key
            layout_data["nodes"][node_name] = {
                "x": pos.x(),
                "y": pos.y(),
                "width": node.rect().width(),
                "height": node.rect().height(),
                "style": style_key,
                "custom_colors": custom_colors if custom_colors else None,
            }

        for edge in self.edges:
            start_name = end_name = None
            for name, node in self.nodes.items():
                if node == edge.start_node:
                    start_name = name
                if node == edge.end_node:
                    end_name = name
            if start_name and end_name:
                layout_data["edges"].append({"source": start_name, "target": end_name})

        path = os.path.join(project_path, "canvas_layout.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(layout_data, f, indent=2, ensure_ascii=False)
            logger.info("画布布局已保存到: %s", path)
        except Exception as e:
            logger.info("保存布局失败: %s", e)

        self._save_color_settings()

    def load_layout(self, project_path):
        if not project_path:
            return

        layout_file = os.path.join(project_path, "canvas_layout.json")
        if not os.path.exists(layout_file):
            self._load_color_settings(project_path)
            return

        try:
            self._load_color_settings(project_path)

            with open(layout_file, "r", encoding="utf-8") as f:
                layout_data = json.load(f)

            # ---- 画布尺寸 ----
            canvas_size = layout_data.get("canvas_size")
            if canvas_size:
                new_w = canvas_size.get("width", self.canvas_width)
                new_h = canvas_size.get("height", self.canvas_height)
                if new_w != self.canvas_width or new_h != self.canvas_height:
                    self.canvas_width = new_w
                    self.canvas_height = new_h
                    hw, hh = self.canvas_width // 2, self.canvas_height // 2
                    saved_nodes = {
                        name: {"item": node, "pos": node.pos(), "rect": node.rect()}
                        for name, node in self.nodes.items()
                    }
                    old_scene = self.scene
                    self.scene = QGraphicsScene(-hw, -hh, self.canvas_width, self.canvas_height, self)
                    self.setScene(self.scene)
                    for name, d in saved_nodes.items():
                        old_scene.removeItem(d["item"])
                        self.scene.addItem(d["item"])
                        d["item"].setPos(d["pos"])
                    saved_edges = self.edges[:]
                    self.edges = []
                    for e in saved_edges:
                        old_scene.removeItem(e)
                        self.scene.addItem(e)
                        self.edges.append(e)
                    logger.info("画布尺寸已更新: %dx%d", self.canvas_width, self.canvas_height)

            # ---- 节点位置 + 颜色 ----
            for node_name, pos_data in layout_data.get("nodes", {}).items():
                if node_name in self.nodes:
                    node = self.nodes[node_name]
                    node.setPos(pos_data["x"], pos_data["y"])
                    # 恢复节点样式
                    sk = pos_data.get("style", "rect")
                    from ui.canvas.items.node_style import STYLES
                    st_cls = STYLES.get(sk, STYLES["rect"])
                    if type(node._style).__name__ != st_cls.__name__:
                        ns = st_cls()
                        node._style = ns
                        ns.node_width = node.rect().width()
                        ns.node_height = node.rect().height()
                        ns.apply(node)
                        ns.apply_status(node, node.status)
                    cc = pos_data.get("custom_colors")
                    if cc and self.parent_window and node_name in self.parent_window.nodes_data:
                        config = self.parent_window.nodes_data[node_name].get("config", {})
                        for key, cfg_key, action in [
                            ("bg", "custom_bg_color", lambda c: node.setBrush(QBrush(c))),
                            ("border", "custom_border_color", lambda c: node.setPen(QPen(c, 2))),
                            ("text", "custom_text_color", lambda c: node.name_text.setDefaultTextColor(c)),
                        ]:
                            if key in cc:
                                try:
                                    color = QColor(cc[key])
                                    if color.isValid():
                                        action(color)
                                        config[cfg_key] = cc[key]
                                except Exception:
                                    pass

            # ---- 自动添加缺失节点 ----
            nodes_added = 0
            for node_name, pos_data in layout_data.get("nodes", {}).items():
                if node_name not in self.nodes and self.parent_window and node_name in self.parent_window.nodes_data:
                    info = self.parent_window.nodes_data[node_name]
                    lang = self.detect_language(info["path"])
                    status = info.get("status", "stopped")
                    x, y = pos_data.get("x", 200), pos_data.get("y", 150)
                    w, h = pos_data.get("width", 140), pos_data.get("height", 80)
                    sk = pos_data.get("style", "rect")
                    from ui.canvas.items.node_style import STYLES
                    st_cls = STYLES.get(sk, STYLES["rect"])
                    node = NodeItem(node_name, lang, status, 0, 0, w, h, self, style=st_cls())
                    node.on_expand_requested = self.on_node_expand_requested
                    node.setPos(x, y)
                    self.scene.addItem(node)
                    self.nodes[node_name] = node
                    nodes_added += 1
                    logger.info("自动恢复节点: %s (位置: %d, %d)", node_name, x, y)

            # ---- 连线 ----
            existing = set()
            for e in self.edges:
                sn = tn = None
                for n, nd in self.nodes.items():
                    if nd == e.start_node: sn = n
                    if nd == e.end_node: tn = n
                if sn and tn: existing.add((sn, tn))
            for ed in layout_data.get("edges", []):
                sn, tn = ed.get("source"), ed.get("target")
                if (sn, tn) in existing: continue
                if sn in self.nodes and tn in self.nodes:
                    edge = EdgeItem(self.nodes[sn], self.nodes[tn])
                    self.scene.addItem(edge)
                    self.edges.append(edge)
                    edge.update_path()

            logger.info("加载完成: %d个节点, %d条连线", len(self.nodes), len(self.edges))

            # ---- 视图状态 ----
            vs = layout_data.get("view_state", {})
            if vs:
                scale = vs.get("scale", 1.0)
                if scale != 1.0:
                    self.resetTransform()
                    self.scale(scale, scale)
                self.horizontalScrollBar().setValue(vs.get("scroll_x", 0))
                self.verticalScrollBar().setValue(vs.get("scroll_y", 0))
                cx, cy = vs.get("center_x"), vs.get("center_y")
                if cx is not None and cy is not None:
                    vp = self.viewport().rect().center()
                    tp = self.mapFromScene(QPointF(cx, cy))
                    dx, dy = tp.x() - vp.x(), tp.y() - vp.y()
                    self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + int(dx))
                    self.verticalScrollBar().setValue(self.verticalScrollBar().value() + int(dy))

            logger.info("画布视图状态已恢复")

        except (json.JSONDecodeError, IOError) as e:
            logger.info("布局文件损坏: %s", e)

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
from ui.core.connection_inferrer import ConnectionInferrer
from ui.core.i18n import t


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
                ed = {"source": start_name, "target": end_name}
                # 保存折叠点
                wp_data = edge.to_dict() if hasattr(edge, 'to_dict') else {}
                if wp_data:
                    ed.update(wp_data)
                layout_data["edges"].append(ed)

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
                    # 节点已存在，更新位置和样式
                    node = self.nodes[node_name]
                    node.setPos(pos_data["x"], pos_data["y"])
                    node.canvas = self  # 关键：设置画布引用，确保节点移动时更新连线
                    # 修复：确保子控件正确挂载和事件绑定
                    node.on_expand_requested = self.on_node_expand_requested  # 确保展开按钮事件绑定
                    for child in node.childItems():
                        child.setParentItem(node)
                        child.setEnabled(True)
                        child.setVisible(True)
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
                elif self.parent_window and node_name in self.parent_window.nodes_data:
                    # 节点不存在但存在于项目数据中，添加到画布
                    from ui.canvas.items.node_item import NodeItem
                    config = self.parent_window.nodes_data[node_name]['config']
                    node_lang = config.get('language', 'python')
                    
                    # 创建节点
                    node = NodeItem(node_name, node_lang)
                    node.setPos(pos_data["x"], pos_data["y"])
                    
                    # 应用样式
                    sk = pos_data.get("style", "rect")
                    from ui.canvas.items.node_style import STYLES
                    st_cls = STYLES.get(sk, STYLES["rect"])
                    node._style = st_cls()
                    node._style.apply(node)
                    
                    # 应用颜色
                    cc = pos_data.get("custom_colors")
                    if cc:
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
                                except:
                                    pass
                    
                    # 添加到画布和节点字典
                    self.scene.addItem(node)
                    self.nodes[node_name] = node
                    node.canvas = self  # 关键：设置画布引用，确保节点移动时更新连线
                    # 修复：确保子控件正确挂载和事件绑定
                    node.on_expand_requested = self.on_node_expand_requested  # 确保展开按钮事件绑定
                    for child in node.childItems():
                        child.setParentItem(node)
                        child.setEnabled(True)
                        child.setVisible(True)
                    logger.info(f"从布局文件添加节点: {node_name} (位置: {pos_data['x']}, {pos_data['y']})")

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
                    node.canvas = self  # 关键：设置画布引用，确保节点移动时更新连线
                    # 修复：确保子控件正确挂载和事件绑定
                    node.on_expand_requested = self.on_node_expand_requested  # 确保展开按钮事件绑定
                    for child in node.childItems():
                        child.setParentItem(node)
                        child.setEnabled(True)
                        child.setVisible(True)
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
                    source_node = self.nodes[sn]
                    target_node = self.nodes[tn]
                    edge = EdgeItem(source_node, target_node, self)
                    # 恢复折叠点（使用延迟同步模式，不立即调用 _sync_abs_to_rel）
                    if hasattr(edge, 'from_dict'):
                        # 使用 defer_sync=True 延迟同步，确保锚点坐标就绪后再转换
                        edge.from_dict(ed, defer_sync=True)
                    self.scene.addItem(edge)
                    self.edges.append(edge)
                    # 初始更新 - 此时使用绝对坐标，_all_points 会自动转换为相对坐标
                    edge.update_path()
            
            # ---- 双向绑定校验 ----
            self._validate_edge_anchor_binding()

            # ---- config.json 兜底校验 ----
            if self.parent_window and self.parent_window.nodes_data:
                try:
                    inferrer = ConnectionInferrer(project_path, self.parent_window.nodes_data)
                    config_edges = inferrer.infer_all_edges()
                    config_set = {(e["source"], e["target"]) for e in config_edges}

                    # 重建画布当前连线集合
                    canvas_set = set()
                    for e in self.edges:
                        sn = tn = None
                        for n, nd in self.nodes.items():
                            if nd == e.start_node: sn = n
                            if nd == e.end_node: tn = n
                        if sn and tn: canvas_set.add((sn, tn))

                    # config 有但画布没有 → 自动补充
                    added = 0
                    for src, tgt in (config_set - canvas_set):
                        if src in self.nodes and tgt in self.nodes:
                            # 避免重复
                            already = False
                            for e in self.edges:
                                if e.start_node == self.nodes[src] and e.end_node == self.nodes[tgt]:
                                    already = True
                                    break
                            if not already:
                                edge = EdgeItem(self.nodes[src], self.nodes[tgt])
                                self.scene.addItem(edge)
                                self.edges.append(edge)
                                edge.update_path()
                                added += 1
                                logger.info("[Config兜底] 补充缺失连线: %s → %s", src, tgt)

                    # 画布有但 config 没有 → 警告（不自动删除，避免误删手动连线）
                    stale = canvas_set - config_set
                    if stale:
                        stale_list = ", ".join(f"{s}→{t}" for s, t in stale)
                        logger.warning(
                            "[Config兜底] 画布存在但config中无listen_upper_file对应的连线: %s",
                            stale_list
                        )

                    if added > 0 or stale:
                        logger.info(
                            "[Config兜底] 校验完成: 补充%d条, 可疑%d条",
                            added, len(stale)
                        )
                except Exception as e:
                    logger.warning("[Config兜底] 校验失败: %s", e)

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

            # ---- 强制刷新所有连线路径 ----
            # 确保加载完成后所有连线端点坐标正确
            for edge in self.edges:
                edge.update_path()
            
            logger.info(t("k_log_view_restored"))

        except (json.JSONDecodeError, IOError) as e:
            logger.info("布局文件损坏: %s", e)
    
    def _validate_edge_anchor_binding(self):
        """校验并修复连线与锚点的双向绑定关系"""
        fixed_count = 0
        
        for edge in self.edges:
            # 检查锚点引用是否正确
            if not edge.start_anchor or not edge.end_anchor:
                # 重新建立锚点引用
                if hasattr(edge.start_node, 'output_anchor'):
                    edge.start_anchor = edge.start_node.output_anchor
                if hasattr(edge.end_node, 'input_anchor'):
                    edge.end_anchor = edge.end_node.input_anchor
            
            # 检查连线是否已注册到锚点
            needs_fix = False
            if edge.start_anchor and edge not in edge.start_anchor.edges:
                edge.start_anchor.add_edge(edge)
                needs_fix = True
            if edge.end_anchor and edge not in edge.end_anchor.edges:
                edge.end_anchor.add_edge(edge)
                needs_fix = True
            
            if needs_fix:
                fixed_count += 1
        
        if fixed_count > 0:
            logger.info("[绑定校验] 修复了 %d 条连线的锚点绑定", fixed_count)
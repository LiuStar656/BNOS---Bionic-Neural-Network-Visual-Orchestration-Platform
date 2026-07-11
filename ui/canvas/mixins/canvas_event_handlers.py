"""事件处理器（组合模式，从 NodeCanvas 拆分）

职责：
- 鼠标事件处理（mousePress / mouseMove / mouseRelease / mouseDoubleClick）
- 键盘事件处理（keyPress / keyRelease - 空格快捷键模式）
- 滚轮事件（wheelEvent - 缩放 / 触控板平移）
- 窗口事件（resizeEvent - 绘图工具栏适配）
- 辅助方法（reset_view / _load_draw_toolbar_config / _toggle_draw_toolbar / _auto_save_layout）

使用方式（由 NodeCanvas __init__ 初始化）：

    self.events = EventHandlers(self)
    # 在 Qt 虚函数中转发：
    def mousePressEvent(self, event):
        self.events.mousePressEvent(event)
    ...
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen, QColor

from ui.core.logger import logger
from ui.core.config.app_config import AppConfig
from ui.canvas.items.node_item import NodeItem
from ui.canvas.items.edge_item import EdgeItem
from ui.canvas.items.anchor_item import AnchorItem
from ui.canvas.items.composite_node_item import CompositeNodeItem


class EventHandlers:
    """鼠标 / 键盘 / 滚轮 / 窗口事件处理器

    组合模式：持有对 canvas 的引用，通过 self.canvas 访问画布状态
    """

    def __init__(self, canvas):
        self.canvas = canvas

    # ── 鼠标事件 ──

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 处理平移、框选和连线拖拽"""
        if self.canvas.draw_layer.mouse_move(event):
            return
        # 如果正在平移（空格+左键拖拽）
        if self.canvas.is_pan_mode and self.canvas.pan_start_pos:
            delta = event.pos() - self.canvas.pan_start_pos
            h_scroll = self.canvas.horizontalScrollBar()
            v_scroll = self.canvas.verticalScrollBar()
            h_scroll.setValue(h_scroll.value() - delta.x())
            v_scroll.setValue(v_scroll.value() - delta.y())
            self.canvas.pan_start_pos = event.pos()
            event.accept()
            return

        # 如果正在框选（左键长按拖拽）
        if (
            self.canvas.is_box_selecting
            and self.canvas.box_select_rect
            and self.canvas.box_select_start_pos
        ):
            from PySide6.QtCore import QRect

            current_pos = event.pos()
            widget_rect = QRect(self.canvas.box_select_start_pos, current_pos).normalized()
            top_left = self.canvas.mapToScene(widget_rect.topLeft())
            bottom_right = self.canvas.mapToScene(widget_rect.bottomRight())
            from PySide6.QtCore import QRectF

            scene_rect = QRectF(top_left, bottom_right)
            self.canvas.box_select_rect.setRect(scene_rect)

            self.canvas.scene.clearSelection()
            for node_name, node in self.canvas.nodes.items():
                node_rect = node.sceneBoundingRect()
                if scene_rect.intersects(node_rect):
                    node.setPen(QPen(QColor(self.canvas.node_selected_color), 3))
                    node.setSelected(True)
                else:
                    node.setPen(QPen(QColor(self.canvas.node_border_color), 2))
                    node.setSelected(False)

            from ui.canvas.drawing.graphic_items import GraphicBase
            for g in self.canvas.draw_layer.graphics:
                if scene_rect.intersects(g.sceneBoundingRect()):
                    g.setSelected(True)
                else:
                    g.setSelected(False)
                    g.selected_handle = -1

            event.accept()
            return

        # 如果正在连线中，更新临时连线的终点跟随鼠标
        if (
            self.canvas.is_connecting
            and self.canvas.temp_edge
            and self.canvas.connect_source
        ):
            from PySide6.QtGui import QPainterPath

            scene_pos = self.canvas.mapToScene(event.position().toPoint())
            source_anchor = getattr(self.canvas, '_connect_source_anchor', None)
            if source_anchor is None:
                source_anchor = self.canvas.connect_source.output_anchor
            anchor_center = source_anchor.boundingRect().center()
            start_pos = source_anchor.mapToScene(anchor_center)

            path = QPainterPath(start_pos)
            path.lineTo(scene_pos)

            self.canvas.temp_edge.setPath(path)
            self.canvas.viewport().update()
            event.accept()
            return

        # 默认处理（拖拽平移等）
        super(type(self.canvas), self.canvas).mouseMoveEvent(event)

        # Group movement: if a node in an expanded composite was dragged,
        # move all sibling nodes by the same delta
        self._sync_composite_group_movement()

    def mousePressEvent(self, event):
        """鼠标按下事件 - 处理空格+左键平移、左键长按框选"""
        if self.canvas.draw_layer.mouse_press(event):
            return
        item = self.canvas.itemAt(event.position().toPoint())

        # 连线模式：点击锚点→完成连接，点击节点/连线→完成连接（默认锚点），否则取消
        if self.canvas.is_connecting and event.button() == Qt.MouseButton.LeftButton:
            target_node = None
            clicked_anchor = None
            scene_pos = self.canvas.mapToScene(event.position().toPoint())
            for probe in self.canvas.items(event.position().toPoint()):
                if probe is self.canvas.temp_edge:
                    continue
                if isinstance(probe, AnchorItem):
                    clicked_anchor = probe
                    parent = probe.parentItem()
                    while parent is not None:
                        if isinstance(parent, (NodeItem, CompositeNodeItem)):
                            target_node = parent
                            break
                        parent = parent.parentItem()
                    break
                if isinstance(probe, (NodeItem, CompositeNodeItem)):
                    target_node = probe
                    break
                if isinstance(probe, EdgeItem):
                    target_node = probe.end_node
                    break
            # Fallback: if anchor not precisely clicked but node/composite hit
            if target_node is not None and clicked_anchor is None:
                local_pos = target_node.mapFromScene(scene_pos)
                clicked_anchor = target_node.find_nearest_input_anchor(
                    local_pos, max_dist=60
                )
                if clicked_anchor is None and hasattr(target_node, 'anchor_manager'):
                    if target_node.anchor_manager.input_anchors:
                        input_list = list(target_node.anchor_manager.input_anchors.values())
                        if len(input_list) == 1:
                            clicked_anchor = input_list[0]
            logger.debug(
                "mousePress: item=%s, target_node=%s, anchor=%s (port=%s), connect_source=%s",
                type(item).__name__,
                target_node.node_name if target_node else None,
                "ok" if clicked_anchor else "None",
                getattr(clicked_anchor, 'port_name', None),
                self.canvas.connect_source.node_name if self.canvas.connect_source else None,
            )
            if target_node and target_node != self.canvas.connect_source:
                self.canvas.complete_connection_to_input(target_node, clicked_anchor)
                logger.debug("连线完成到 %s", target_node.node_name)
                event.accept()
                return
            self.canvas.cancel_connection()
            logger.debug("取消连线")
            event.accept()
            return

        # 空格+左键：两阶段触发机制（进入平移模式）
        if event.button() == Qt.MouseButton.LeftButton and self.canvas.space_mode_active:
            # 如果点击的是节点、连线或锚点，不进入平移模式，交给子项处理
            if item is not None and (
                isinstance(item, NodeItem)
                or isinstance(item, EdgeItem)
                or isinstance(item, AnchorItem)
            ):
                return

            # 进入平移模式（第二阶段）
            self.canvas.is_pan_mode = True
            self.canvas.pan_start_pos = event.position().toPoint()
            self.canvas.setCursor(Qt.CursorShape.ClosedHandCursor)

            # 临时禁用所有节点的移动标志，防止节点被拖动
            for node in self.canvas.nodes.values():
                node.setFlag(NodeItem.GraphicsItemFlag.ItemIsMovable, False)

            logger.debug("进入平移模式（空格模式+左键）")
            event.accept()
            return

        # Alt+左键：框选模式（仅在未按空格时）
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not self.canvas.is_space_pressed
            and event.modifiers() & Qt.KeyboardModifier.AltModifier
        ):
            # 沿 parentItem 链上溯，排除交互项
            is_interactive = False
            probe = item
            while probe is not None:
                if isinstance(probe, (NodeItem, EdgeItem, AnchorItem, CompositeNodeItem)):
                    is_interactive = True
                    break
                probe = probe.parentItem()

            if not is_interactive:
                self.canvas.clear_box_selection()
                self.canvas.is_box_selecting = True
                self.canvas.box_select_start_pos = event.position().toPoint()

                from PySide6.QtWidgets import QGraphicsRectItem

                self.canvas.box_select_rect = QGraphicsRectItem()
                self.canvas.box_select_rect.setPen(
                    QPen(QColor("#2196F3"), 1.5, Qt.PenStyle.DashLine)
                )
                self.canvas.box_select_rect.setBrush(QColor(33, 150, 243, 30))
                self.canvas.box_select_rect.setZValue(1)
                self.canvas.scene.addItem(self.canvas.box_select_rect)
                logger.debug("开始框选")
                event.accept()
                return

        # 左键点击空白处 → 取消所有选中
        if event.button() == Qt.MouseButton.LeftButton and item is None:
            self.canvas.clear_box_selection()
            self.canvas.scene.clearSelection()
            event.accept()
            return

        # 点击复合节点的锚点 → 开始/完成连线
        if event.button() == Qt.MouseButton.LeftButton and isinstance(item, AnchorItem):
            comp_parent = item.parentItem()
            if isinstance(comp_parent, CompositeNodeItem):
                anchor = item
                if getattr(anchor, 'port_type', '') == 'output':
                    # Start connection from composite output
                    logger.debug("CompositeNodeItem[%s]: output anchor %s clicked",
                                 comp_parent.comp_id, getattr(anchor, 'port_name', ''))
                    self.canvas.start_connection_from_output(comp_parent, anchor)
                    event.accept()
                    return
                elif self.canvas.is_connecting and getattr(anchor, 'port_type', '') == 'input':
                    # Complete connection to composite input
                    logger.debug("CompositeNodeItem[%s]: input anchor %s connected",
                                 comp_parent.comp_id, getattr(anchor, 'port_name', ''))
                    if self.canvas.connect_source != comp_parent:
                        self.canvas.complete_connection_to_input(comp_parent, anchor)
                    event.accept()
                    return

        # Pre-set drag anchor for expanded composite internal nodes
        self._prepare_composite_drag_anchor(item)

        # 其他情况：交给默认处理或子项处理
        super(type(self.canvas), self.canvas).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件 - 结束平移或框选"""
        if self.canvas.draw_layer.mouse_release(event):
            return
        # 结束平移模式（第二阶段退出）
        if self.canvas.is_pan_mode and event.button() == Qt.MouseButton.LeftButton:
            self.canvas.is_pan_mode = False
            self.canvas.pan_start_pos = None
            if self.canvas.space_mode_active:
                self.canvas.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.canvas.setCursor(Qt.CursorShape.ArrowCursor)

            # 恢复所有节点的移动标志
            for node in self.canvas.nodes.values():
                node.setFlag(NodeItem.GraphicsItemFlag.ItemIsMovable, True)

            logger.debug("退出平移模式")

            # 自动保存布局（包含视图状态）
            if (
                self.canvas.parent_window
                and self.canvas.parent_window.current_project_path
            ):
                self.canvas._save_timer.stop()
                self.canvas._save_timer.start(500)

            event.accept()
            return

        # 结束框选模式
        if self.canvas.is_box_selecting and event.button() == Qt.MouseButton.LeftButton:
            self.canvas.is_box_selecting = False
            if self.canvas.box_select_rect:
                self.canvas.scene.removeItem(self.canvas.box_select_rect)
                self.canvas.box_select_rect = None
            self.canvas.box_select_start_pos = None
            if self.canvas.box_selected_nodes:
                logger.debug(
                    "结束框选，选中 %d 个节点: %s",
                    len(self.canvas.box_selected_nodes),
                    self.canvas.box_selected_nodes,
                )
            else:
                logger.debug("结束框选，未选中节点")
            event.accept()
            return

        super(type(self.canvas), self.canvas).mouseReleaseEvent(event)

        # Clear drag anchor positions for all composites
        self._clear_composite_drag_anchors()

    # ── Composite group movement ──

    def _prepare_composite_drag_anchor(self, item):
        """If the pressed item is a NodeItem in an expanded composite,
        pre-snapshot all sibling positions as drag anchors.

        Called from mousePressEvent BEFORE the drag starts, so the
        first mouseMoveEvent already has valid anchors.
        """
        if not isinstance(item, NodeItem):
            return
        node_name = getattr(item, 'node_name', None)
        if not node_name:
            return
        mgr = getattr(self.canvas, '_composite_manager', None)
        if not mgr:
            return

        for comp_id, comp in mgr._composites.items():
            if not comp.get("_expanded"):
                continue
            node_names = comp.get("nodes", [])
            if node_name not in node_names:
                continue
            # Found the composite this node belongs to
            anchor = {}
            for n in node_names:
                node_item = self.canvas.nodes.get(n)
                if node_item and node_item.isVisible():
                    anchor[n] = (node_item.pos().x(), node_item.pos().y())
            comp["_drag_anchor_positions"] = anchor
            return

    def _sync_composite_group_movement(self):
        """When an expanded composite node's internal node is dragged,
        move all sibling nodes and the group frame by the same delta.

        Anchor positions are pre-set in mousePressEvent and updated
        every frame to avoid feedback loops.
        """
        mgr = getattr(self.canvas, '_composite_manager', None)
        if not mgr:
            return

        if getattr(self.canvas, '_group_moving', False):
            return

        for comp_id, comp in mgr._composites.items():
            if not comp.get("_expanded"):
                continue

            node_names = comp.get("nodes", [])
            if not node_names:
                continue

            anchor = comp.get("_drag_anchor_positions")
            if not anchor:
                continue

            # Find which node was moved (position differs from anchor)
            drag_dx = drag_dy = 0
            dragged_node = None
            for n in node_names:
                item = self.canvas.nodes.get(n)
                if not item or not item.isVisible():
                    continue
                orig = anchor.get(n)
                if orig is None:
                    continue
                dx = item.pos().x() - orig[0]
                dy = item.pos().y() - orig[1]
                if abs(dx) > 0.1 or abs(dy) > 0.1:
                    dragged_node = n
                    drag_dx = dx
                    drag_dy = dy
                    break

            if dragged_node is None:
                continue

            # Apply the SAME delta to ALL siblings (skip dragged node, already moved by Qt)
            self.canvas._group_moving = True
            try:
                for n in node_names:
                    if n == dragged_node:
                        # Already positioned by Qt's drag mechanism — just update anchor
                        item = self.canvas.nodes.get(n)
                        if item and item.isVisible():
                            anchor[n] = (item.pos().x(), item.pos().y())
                        continue
                    orig = anchor.get(n)
                    if orig is None:
                        continue
                    item = self.canvas.nodes.get(n)
                    if item and item.isVisible():
                        item.setPos(orig[0] + drag_dx, orig[1] + drag_dy)
                        # Update anchor to reflect applied position
                        anchor[n] = (orig[0] + drag_dx, orig[1] + drag_dy)

                # Update group frame bounds
                frame_key = f"__frame__{comp_id}"
                frame = self.canvas.nodes.get(frame_key)
                if frame and hasattr(frame, 'update_for_items'):
                    visible_items = [self.canvas.nodes[n] for n in node_names
                                     if n in self.canvas.nodes and self.canvas.nodes[n].isVisible()]
                    frame.update_for_items(visible_items)
            finally:
                self.canvas._group_moving = False

    def _clear_composite_drag_anchors(self):
        """Clear drag anchor positions for all expanded composites."""
        mgr = getattr(self.canvas, '_composite_manager', None)
        if not mgr:
            return
        for comp in mgr._composites.values():
            if "_drag_anchor_positions" in comp:
                del comp["_drag_anchor_positions"]

    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件 - 双击节点打开配置对话框"""
        if self.canvas.draw_layer.mouse_double_click(event):
            return
        item = self.canvas.itemAt(event.position().toPoint())
        if isinstance(item, NodeItem):
            node_name = item.node_name
            logger.debug("双击节点: %s，打开配置对话框", node_name)
            self.canvas.open_node_config(node_name)
            event.accept()
            return
        super(type(self.canvas), self.canvas).mouseDoubleClickEvent(event)

    # ── 键盘事件 ──

    def keyPressEvent(self, event):
        """键盘按下事件 - 空格进入快捷键模式"""
        if self.canvas.draw_layer.key_press(event):
            return
        if event.key() == Qt.Key.Key_Space:
            # 使用 Qt 内置 isAutoRepeat() 过滤系统自动重复事件
            if event.isAutoRepeat():
                event.accept()
                return
            # 首次按下空格（非自动重复），进入空格快捷键模式
            self.canvas.is_space_pressed = True
            self.canvas.space_mode_active = True
            logger.debug("进入空格快捷键模式")
            if not self.canvas.is_pan_mode:
                self.canvas.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super(type(self.canvas), self.canvas).keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """键盘释放事件 - 跟踪空格键状态"""
        if self.canvas.draw_layer.key_release(event):
            return
        if event.key() == Qt.Key.Key_Space:
            # 使用 Qt 内置 isAutoRepeat() 过滤虚假释放事件
            if event.isAutoRepeat():
                event.accept()
                return
            self.canvas.is_space_pressed = False
            self.canvas.space_mode_active = False
            if self.canvas.is_pan_mode:
                self.canvas.is_pan_mode = False
                self.canvas.pan_start_pos = None
                self.canvas.setCursor(Qt.CursorShape.ArrowCursor)
                for node in self.canvas.nodes.values():
                    node.setFlag(NodeItem.GraphicsItemFlag.ItemIsMovable, True)
                logger.debug("退出平移模式（空格键释放）")
            else:
                self.canvas.setCursor(Qt.CursorShape.ArrowCursor)
            logger.debug("退出空格快捷键模式")
            event.accept()
            return
        super(type(self.canvas), self.canvas).keyReleaseEvent(event)

    # ── 滚轮事件 ──

    def wheelEvent(self, event):
        """滚轮事件 - Ctrl+滚轮缩放，触控板/滚轮平移"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+滚轮：放大缩小
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            current_scale = self.canvas.transform().m11()
            new_scale = current_scale * factor
            if 0.1 <= new_scale <= 5.0:
                self.canvas.scale(factor, factor)
                if (
                    self.canvas.parent_window
                    and self.canvas.parent_window.current_project_path
                ):
                    self.canvas._save_timer.stop()
                    self.canvas._save_timer.start(500)
            event.accept()
        else:
            # 触控板/滚轮平移
            pixel_delta = event.pixelDelta()
            if not pixel_delta.isNull():
                scroll_x = pixel_delta.x()
                scroll_y = pixel_delta.y()
            else:
                angle_delta = event.angleDelta()
                scroll_x = angle_delta.x()
                scroll_y = angle_delta.y()

            h_scroll = self.canvas.horizontalScrollBar()
            v_scroll = self.canvas.verticalScrollBar()
            if not pixel_delta.isNull():
                h_scroll.setValue(h_scroll.value() - scroll_x)
                v_scroll.setValue(v_scroll.value() - scroll_y)
            else:
                h_scroll.setValue(h_scroll.value() - scroll_x)
                v_scroll.setValue(v_scroll.value() - scroll_y)

            if (
                self.canvas.parent_window
                and self.canvas.parent_window.current_project_path
            ):
                self.canvas._save_timer.stop()
                self.canvas._save_timer.start(500)
            event.accept()

    # ── 窗口事件 ──

    def resizeEvent(self, event):
        super(type(self.canvas), self.canvas).resizeEvent(event)
        self.canvas.draw_layer.resize_toolbar()

    # ── 辅助方法 ──

    def reset_view(self):
        """重置视图到默认状态"""
        self.canvas.resetTransform()
        self.canvas.centerOn(0, 0)
        logger.info("[OK] 视图已重置")

    def _load_draw_toolbar_config(self):
        """从 app_config 加载绘图工具栏显示状态"""
        try:
            app_config = AppConfig()
            visible = app_config.get("draw_toolbar_visible", False)
            if visible:
                self.canvas.draw_layer.show_toolbar()
            else:
                self.canvas.draw_layer.hide_toolbar()
            logger.debug("绘图工具栏状态已从配置恢复: %s", visible)
        except Exception as e:
            logger.warning("加载绘图工具栏配置失败: %s", e)

    def _toggle_draw_toolbar(self):
        """切换绘图工具栏显示/隐藏"""
        if hasattr(self.canvas, 'draw_layer'):
            self.canvas.draw_layer.toggle_toolbar()

    def _auto_save_layout(self):
        """自动保存布局（防抖定时器回调"""
        if self.canvas.parent_window and self.canvas.parent_window.current_project_path:
            for i, edge in enumerate(self.canvas.edges):
                ep = getattr(edge.end_anchor, 'port_name', None) if edge.end_anchor else None
                logger.debug("[auto_save] edge#%d end_anchor.port_name=%s", i, ep)
            self.canvas.save_layout(self.canvas.parent_window.current_project_path)

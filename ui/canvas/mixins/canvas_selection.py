"""画布选择管理与命令录制（组合模式，从 NodeCanvas 拆分）

职责：
- 节点选择状态管理（单击选中 / Ctrl+单击多选 / 获取选中 / 清除选中）
- 命令录制（undo/redo 期间的创建/删除节点/连线命令录制）

使用方式（由 NodeCanvas __init__ 初始化）：

    self.selection = SelectionManager(self)
    # 调用方式：
    self.selection.on_node_selected(node)
    self.selection._toggle_node_selection(name)
    self.selection.get_selected_node()
    self.selection.clear_selection()
    self.selection._begin_replay()
    self.selection._end_replay()
    self.selection._record_create_node(name)
    self.selection._record_delete_node(name)
    self.selection._record_create_edge(src, tgt)
    self.selection._record_delete_edge(src, tgt, ...)

注意：内部状态（_replay_depth）由 SelectionManager 管理，
但 box_selected_nodes 保留在 NodeCanvas 中（因为事件处理器也需要访问）
通过 self.canvas.box_selected_nodes 访问。
"""
from PySide6.QtGui import QPen, QColor

from ui.core.logger import logger


class SelectionManager:
    """节点选择管理与命令录制

    组合模式：持有对 canvas 的引用，通过 self.canvas 访问画布状态
    """

    def __init__(self, canvas):
        self.canvas = canvas
        # 命令重放深度（>0 表示在重放中，不应再次录制命令）
        self._replay_depth = 0

    # ── 节点选择 ──

    def on_node_selected(self, node):
        """普通单击选中节点（单选，清除之前的多选）"""
        # 如果点击的节点已在多选列表中，只取消其他节点的Qt选中，保留此节点可拖动
        if node.node_name in self.canvas.box_selected_nodes:
            # 确保它是唯一被Qt选中的项，支持拖动
            for name in self.canvas.box_selected_nodes:
                if name in self.canvas.nodes:
                    self.canvas.nodes[name].setSelected(name == node.node_name)
            return

        # 清除之前所有选中节点
        for name in self.canvas.box_selected_nodes:
            if name in self.canvas.nodes:
                self.canvas.nodes[name].setPen(
                    QPen(QColor(self.canvas.node_border_color), 2)
                )
                self.canvas.nodes[name].setSelected(False)
        self.canvas.box_selected_nodes = []

        # 选中当前节点
        self.canvas.box_selected_nodes.append(node.node_name)
        node.setPen(QPen(QColor(self.canvas.node_selected_color), 3))
        node.setSelected(True)
        logger.info("选中节点: %s", node.node_name)

    def _toggle_node_selection(self, node_name):
        """切换节点选中状态（用于 Ctrl+单击多选）"""
        if node_name not in self.canvas.nodes:
            return

        node = self.canvas.nodes[node_name]

        if node_name in self.canvas.box_selected_nodes:
            self.canvas.box_selected_nodes.remove(node_name)
            node.setPen(QPen(QColor(self.canvas.node_border_color), 2))
            node.setSelected(False)
            logger.debug("取消选中节点: %s", node_name)
        else:
            self.canvas.box_selected_nodes.append(node_name)
            node.setPen(QPen(QColor(self.canvas.node_selected_color), 3))
            node.setSelected(True)
            logger.info(
                "选中节点: %s (共%d个)",
                node_name,
                len(self.canvas.box_selected_nodes),
            )

    def get_selected_node(self):
        """获取当前选中的节点名称（单选优先取第一个）"""
        return self.canvas.box_selected_nodes[0] if self.canvas.box_selected_nodes else None

    def clear_selection(self):
        """清除节点选择"""
        self.canvas.clear_box_selection()

    # ── 命令录制辅助方法 ──

    def _begin_replay(self):
        """进入命令重放模式（防止 undo/redo 中重复录制命令）"""
        self._replay_depth += 1

    def _end_replay(self):
        """退出命令重放模式"""
        if self._replay_depth > 0:
            self._replay_depth -= 1

    @property
    def _is_replaying(self) -> bool:
        return self._replay_depth > 0

    def _record_create_node(self, node_name: str):
        """录制创建节点命令到历史（仅记录，不二次执行）"""
        if self._is_replaying:
            return
        try:
            from ui.core.commands.node_commands import CreateNodeCommand
            from ui.core.commands.history_manager import history_manager
            if history_manager.state.is_recording:
                history_manager.record_only(CreateNodeCommand(node_name, self.canvas))
        except Exception:
            pass

    def _record_delete_node(self, node_name: str):
        """录制删除节点命令到历史（需在删除前调用以收集状态）"""
        if self._is_replaying:
            return
        try:
            from ui.core.commands.node_commands import DeleteNodeCommand
            from ui.core.commands.history_manager import history_manager
            if history_manager.state.is_recording:
                history_manager.execute_command(
                    DeleteNodeCommand(node_name, self.canvas, self.canvas.parent_window)
                )
        except Exception:
            pass

    def _record_create_edge(self, src_name: str, tgt_name: str):
        """录制创建连线命令到历史（仅记录，不二次执行）"""
        if self._is_replaying:
            return
        try:
            from ui.core.commands.edge_commands import CreateEdgeCommand
            from ui.core.commands.history_manager import history_manager
            if history_manager.state.is_recording:
                history_manager.record_only(CreateEdgeCommand(src_name, tgt_name, self.canvas))
        except Exception:
            pass

    def _record_delete_edge(self, src_name: str, tgt_name: str,
                            target_port_name=None, source_port_name=None):
        """录制删除连线命令到历史（需在删除前调用）"""
        if self._is_replaying:
            return
        try:
            from ui.core.commands.edge_commands import DeleteEdgeCommand
            from ui.core.commands.history_manager import history_manager
            if history_manager.state.is_recording:
                history_manager.execute_command(
                    DeleteEdgeCommand(src_name, tgt_name,
                                      target_port_name, source_port_name, None, self.canvas)
                )
        except Exception:
            pass

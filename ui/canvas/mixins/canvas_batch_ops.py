"""
批量操作 Mixin — 框选节点的批量启动/停止/移除/清除配置
"""

from __future__ import annotations

import json
import os

from ui.core.i18n import t
from ui.core.logger import logger
from ui.core.utils.dialog_utils import themed_message


class CanvasBatchOps:
    """批量操作管理（组合类，通过 self.canvas 访问画布上下文）"""

    def __init__(self, canvas):
        self.canvas = canvas

    # ------------------------------------------------------------------
    # 通用批量操作模板方法
    # ------------------------------------------------------------------

    def _should_skip_node(self, node_name, skip_statuses):
        """检查节点是否应该跳过操作

        Args:
            node_name: 节点名称
            skip_statuses: 应该跳过的状态列表

        Returns:
            tuple: (should_skip, skip_reason)
                - should_skip: 是否跳过
                - skip_reason: "node_not_found" 表示节点不存在应计入失败，
                  "invalid_status" 表示状态不符应计入跳过
        """
        if not self.canvas.parent_window or node_name not in self.canvas.parent_window.nodes_data:
            return True, "node_not_found"

        node_info = self.canvas.parent_window.nodes_data[node_name]
        if node_info["status"] in skip_statuses:
            return True, "invalid_status"

        return False, None

    def _execute_batch_operation(self, operation_name, operation_func, skip_statuses, operation_label=None):
        """执行批量操作的通用模板方法

        Args:
            operation_name: 操作名称（用于 i18n key 拼接）
            operation_func: 执行单个节点操作的 callable，签名为 f(node_name)
            skip_statuses: 应该跳过的状态元组
            operation_label: 操作的中文标签（用于日志），默认使用 operation_name
        """
        if not self.canvas.box_selected_nodes:
            return

        if operation_label is None:
            operation_label = operation_name

        success_count = 0
        skip_count = 0
        fail_count = 0

        for node_name in self.canvas.box_selected_nodes[:]:
            should_skip, skip_reason = self._should_skip_node(node_name, skip_statuses)
            if should_skip:
                if skip_reason == "node_not_found":
                    fail_count += 1
                else:
                    skip_count += 1
                continue

            try:
                operation_func(node_name)
                success_count += 1
            except Exception as e:
                logger.error("%s节点 %s 失败: %s", operation_label, node_name, e)
                fail_count += 1

        self._show_batch_result(operation_name, success_count, skip_count, fail_count)
        self.canvas.selection.clear_selection()

    def _show_batch_result(self, operation_name, success_count, skip_count, fail_count):
        """显示批量操作结果

        Args:
            operation_name: 操作名称（用于 i18n key 拼接）
            success_count: 成功数量
            skip_count: 跳过数量
            fail_count: 失败数量
        """
        result_key = f"_k_batch_{operation_name}_result"
        title_key = f"k_title_batch_{operation_name}_result"

        result_msg = t(result_key).format(success=success_count, skip=skip_count, fail=fail_count)
        themed_message(self.canvas, t(title_key), result_msg, "info")

    # ------------------------------------------------------------------
    # 批量启动 / 停止
    # ------------------------------------------------------------------

    def batch_start_selected_nodes(self):
        """批量启动选中的节点"""
        self._execute_batch_operation(
            operation_name="start",
            operation_func=self.canvas.parent_window.start_selected_node_by_name,
            skip_statuses=("running", "idle"),
            operation_label="启动",
        )

    def batch_stop_selected_nodes(self):
        """批量停止选中的节点（包括运行中、空闲、排队中、启动中的节点）"""
        self._execute_batch_operation(
            operation_name="stop",
            operation_func=self.canvas.parent_window.stop_selected_node_by_name,
            skip_statuses=("stopped",),
            operation_label="停止",
        )

    # ------------------------------------------------------------------
    # 批量移除节点
    # ------------------------------------------------------------------

    def _get_running_nodes(self, node_names):
        """获取运行中的节点列表

        Args:
            node_names: 节点名称列表

        Returns:
            list: 运行中的节点名称列表
        """
        running_nodes = []
        if self.canvas.parent_window:
            for node_name in node_names:
                nd = self.canvas.parent_window.nodes_data.get(node_name, {})
                if nd.get("status") in ("running", "idle", "starting"):
                    running_nodes.append(node_name)
        return running_nodes

    def _build_remove_confirm_message(self, node_names, running_nodes):
        """构建移除确认消息

        Args:
            node_names: 要移除的节点列表
            running_nodes: 运行中的节点列表

        Returns:
            str: 确认消息内容
        """
        count = len(node_names)
        preview_nodes = node_names[:10]
        nodes_preview = "\n".join([f"  - {name}" for name in preview_nodes])
        if count > 10:
            nodes_preview += f"\n  ... 还有 {count - 10} 个节点"

        confirm_msg = t("_k_batch_remove_confirm").format(count=count, nodes=nodes_preview)

        if running_nodes:
            running_preview = "\n".join(f"  - {n}" for n in running_nodes[:5])
            if len(running_nodes) > 5:
                running_preview += f"\n  ... 还有 {len(running_nodes) - 5} 个"
            confirm_msg = (
                f"以下 {len(running_nodes)} 个节点正在运行，移除将同时停止其进程：\n"
                + running_preview
                + f"\n\n{confirm_msg}"
            )

        return confirm_msg

    def _confirm_remove_nodes(self, node_names, running_nodes):
        """确认是否移除节点

        Args:
            node_names: 要移除的节点列表
            running_nodes: 运行中的节点列表

        Returns:
            bool: 用户是否确认移除
        """
        confirm_msg = self._build_remove_confirm_message(node_names, running_nodes)
        reply = themed_message(self.canvas, t("k_title_confirm_remove_canvas"), confirm_msg, "question")
        return reply

    def _stop_running_nodes(self, running_nodes):
        """停止运行中的节点

        Args:
            running_nodes: 运行中的节点名称列表
        """
        for node_name in running_nodes:
            if self.canvas.parent_window:
                try:
                    self.canvas.parent_window.stop_selected_node_by_name(node_name)
                    logger.info("批量移除前已停止节点: %s", node_name)
                except Exception as e:
                    logger.warning("停止节点 %s 失败: %s", node_name, e)

    def _remove_nodes_from_canvas(self, node_names):
        """从画布移除节点（通过权威的 remove_node_from_canvas 链路）

        对每个节点走 canvas.remove_node_from_canvas 权威方法，确保：
        - 相关连线通过 canvas.remove_edge 完整清理上下游配置
        - 复合节点内部节点列表正确更新
        - 先录制 undo/redo 命令再执行删除

        Args:
            node_names: 要移除的节点名称列表

        Returns:
            int: 实际移除的节点数量
        """
        removed_count = 0
        for node_name in node_names[:]:
            if node_name not in self.canvas.nodes:
                continue
            try:
                self.canvas.selection._record_delete_node(node_name)
            except Exception as e:
                logger.warning("录制删除节点 %s 的 undo 命令失败: %s", node_name, e)
            self.canvas.remove_node_from_canvas(node_name)
            removed_count += 1
            logger.info("已从画布移除节点: %s", node_name)
        return removed_count

    def _trigger_project_save(self):
        """触发项目保存定时器"""
        if self.canvas.parent_window and self.canvas.parent_window.current_project_path:
            self.canvas._save_timer.stop()
            self.canvas._save_timer.start(500)

    def batch_remove_nodes_from_canvas(self):
        """批量从画布移除节点（不删除文件）

        如果包含运行中的节点，在确认后自动停止进程。
        """
        if not self.canvas.box_selected_nodes:
            return

        node_names = self.canvas.box_selected_nodes[:]
        running_nodes = self._get_running_nodes(node_names)

        # 用户确认
        if not self._confirm_remove_nodes(node_names, running_nodes):
            return

        # 停止运行中的节点
        self._stop_running_nodes(running_nodes)

        # 移除节点（内部已通过权威链路删除关联连线）
        removed_count = self._remove_nodes_from_canvas(node_names)

        # 清理选择状态并触发保存
        self.canvas.selection.clear_selection()
        self._trigger_project_save()

        logger.info("已从画布移除 %d 个节点", removed_count)

    # ------------------------------------------------------------------
    # 批量清除监听配置
    # ------------------------------------------------------------------

    def batch_clear_listen_config(self):
        """批量清除选中节点的输入监听配置及画布连线（跨边界双向清理）。

        跨边界双向清理规则（Bug E 修复）：
          - 选中 start 节点 → 即使下游节点未被选中，也要清理下游 listen_upper_file / port_mappings
          - 选中 end   节点 → 即使上游节点未被选中，也要清理上游 out_connections
          - 复合节点涉及的边 → 同步清理 composite.json._port_routing 路由

        所有边删除统一走 CanvasConnections.remove_edge 权威注册链路，
        禁止手动写配置文件，杜绝"只清了一端配置另一端残留"的半更新状态。
        """
        if not self.canvas.box_selected_nodes:
            return

        selected_set = set(self.canvas.box_selected_nodes)
        pw = self.canvas.parent_window
        nodes_data = pw.nodes_data if (pw and pw.nodes_data) else {}

        # ========== 阶段一：按 EdgeKey 语义收集所有与选中集相交的边 ==========
        # 相交条件：edge 的 source OR target 任一节点名在 selected_set 内
        edges_plan: list = []
        seen_edge_ids = set()
        for edge in list(self.canvas.edges):
            # 先解出 source_name / target_name（与 canvas_connections.remove_edge 同一推导逻辑）
            source_name = None
            target_name = None
            for name, node_item in self.canvas.nodes.items():
                if node_item == edge.start_node:
                    source_name = name
                if node_item == edge.end_node:
                    target_name = name
            if not (source_name and target_name):
                continue

            # 命中：任一端在选中集
            if source_name in selected_set or target_name in selected_set:
                eid = id(edge)
                if eid in seen_edge_ids:
                    continue
                seen_edge_ids.add(eid)
                edges_plan.append((edge, source_name, target_name))

        logger.info(
            "[Phase3.3-batch-clear] 选中节点 %s，命中关联边 %d 条（跨边界双向清理）",
            sorted(selected_set),
            len(edges_plan),
        )

        # ========== 阶段二：对每条命中边，走 remove_edge 权威链路 ==========
        # remove_edge 会负责：
        #   - 清理 target listen_upper_file / port_mappings
        #   - 清理 source out_connections
        #   - 清理 composite.json._port_routing（涉及复合节点时）
        #   - 注销 NodeStateManager._edge_keys 条目
        #   - EdgeConfigWriter 灰度双写 RouteCache
        removed_count = 0
        for edge, src, tgt in edges_plan:
            try:
                self.canvas.connections.remove_edge(edge)
                removed_count += 1
                logger.info(
                    "[Phase3.3-batch-clear] removed edge %s -> %s (cross-boundary clean OK)",
                    src,
                    tgt,
                )
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "[Phase3.3-batch-clear] remove_edge %s -> %s failed: %s",
                    src,
                    tgt,
                    e,
                )

        # ========== 阶段三：兜底清选中节点内存配置（防御性，防止 remove_edge 漏网）==========
        cleared_count = 0
        for node_name in list(selected_set):
            if not (pw and node_name in nodes_data):
                continue
            node_info = nodes_data[node_name]
            config = node_info.get("config") or {}
            need_save = False

            if config.get("listen_upper_file"):
                config["listen_upper_file"] = ""
                need_save = True
                cleared_count += 1

            if isinstance(config.get("port_mappings"), dict) and config["port_mappings"]:
                config["port_mappings"] = {}
                need_save = True
                cleared_count += 1

            if isinstance(config.get("out_connections"), dict) and config["out_connections"]:
                config["out_connections"] = {}
                need_save = True
                cleared_count += 1

            if need_save:
                config_path = os.path.join(node_info["path"], "node_config.json")
                try:
                    with open(config_path, "w", encoding="utf-8") as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    logger.info(
                        "[Phase3.3-batch-clear] fallback cleared node %s config fields",
                        node_name,
                    )
                except Exception as e:
                    logger.error("[Phase3.3-batch-clear] fallback save config %s failed: %s", node_name, e)

        msg_count = max(removed_count, cleared_count)
        themed_message(
            self.canvas,
            t("k_title_clear_complete"),
            t("_k_config_cleared").format(count=msg_count),
            "info",
        )
        self.canvas.selection.clear_selection()
        self._trigger_project_save()

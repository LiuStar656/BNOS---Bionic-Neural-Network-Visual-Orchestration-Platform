"""
批量操作 Mixin — 框选节点的批量启动/停止/移除/清除配置
"""
import os
import json
from ui.core.utils.dialog_utils import themed_message
from ui.core.logger import logger
from ui.core.i18n import t


class CanvasBatchOpsMixin:
    """批量操作管理（Mixin 注入到 NodeCanvas）"""

    def batch_start_selected_nodes(self):
        """批量启动选中的节点"""
        if not self.box_selected_nodes:
            return

        success_count = 0
        skip_count = 0
        fail_count = 0

        for node_name in self.box_selected_nodes[:]:
            if not self.parent_window or node_name not in self.parent_window.nodes_data:
                fail_count += 1
                continue

            node_info = self.parent_window.nodes_data[node_name]
            if node_info['status'] in ('running', 'idle'):
                skip_count += 1
                continue

            try:
                self.parent_window.start_selected_node_by_name(node_name)
                success_count += 1
            except Exception as e:
                logger.error("启动节点 %s 失败: %s", node_name, e)
                fail_count += 1

        result_msg = t("_k_batch_start_result").format(success=success_count, skip=skip_count, fail=fail_count)
        themed_message(self, t("k_title_batch_start_result"), result_msg, "info")
        self.clear_box_selection()

    def batch_stop_selected_nodes(self):
        """批量停止选中的节点（仅停止正在运行的）"""
        if not self.box_selected_nodes:
            return

        success_count = 0
        skip_count = 0
        fail_count = 0

        for node_name in self.box_selected_nodes[:]:
            if not self.parent_window or node_name not in self.parent_window.nodes_data:
                fail_count += 1
                continue

            node_info = self.parent_window.nodes_data[node_name]
            if node_info['status'] not in ('running', 'idle'):
                skip_count += 1
                continue

            try:
                self.parent_window.stop_selected_node_by_name(node_name)
                success_count += 1
            except Exception as e:
                logger.error("停止节点 %s 失败: %s", node_name, e)
                fail_count += 1

        result_msg = t("_k_batch_stop_result").format(success=success_count, skip=skip_count, fail=fail_count)
        themed_message(self, t("k_title_batch_stop_result"), result_msg, "info")
        self.clear_box_selection()

    def batch_remove_nodes_from_canvas(self):
        """批量从画布移除节点（不删除文件）"""
        if not self.box_selected_nodes:
            return

        count = len(self.box_selected_nodes)
        preview_nodes = self.box_selected_nodes[:10]
        nodes_preview = "\n".join([f"  - {name}" for name in preview_nodes])
        if count > 10:
            nodes_preview += f"\n  ... 还有 {count - 10} 个节点"

        reply = themed_message(self, t("k_title_confirm_remove_canvas"),
            t("_k_batch_remove_confirm").format(count=count, nodes=nodes_preview),
            "question")

        if not reply:
            return

        removed_count = 0
        for node_name in self.box_selected_nodes[:]:
            if node_name in self.nodes:
                node = self.nodes[node_name]
                self.scene.removeItem(node)
                del self.nodes[node_name]
                removed_count += 1
                logger.info("已从画布移除节点: %s", node_name)

        edges_to_remove = []
        for edge in self.edges:
            source_name = None
            target_name = None
            for name, node_item in self.nodes.items():
                if node_item == edge.start_node:
                    source_name = name
                if node_item == edge.end_node:
                    target_name = name
            if source_name not in self.nodes or target_name not in self.nodes:
                edges_to_remove.append(edge)

        for edge in edges_to_remove:
            self.remove_edge(edge)

        logger.info("已从画布移除 %d 个节点", removed_count)
        self.clear_box_selection()

        if self.parent_window and self.parent_window.current_project_path:
            self._save_timer.stop()
            self._save_timer.start(500)

    def batch_clear_listen_config(self):
        """批量清除选中节点的输入监听配置及画布连线（包括 port_mappings 和 listen_upper_file）"""
        if not self.box_selected_nodes:
            return

        cleared_count = 0
        for node_name in self.box_selected_nodes[:]:
            if self.parent_window and node_name in self.parent_window.nodes_data:
                node_info = self.parent_window.nodes_data[node_name]
                config = node_info['config']
                need_save = False

                if config.get('listen_upper_file'):
                    config['listen_upper_file'] = ""
                    need_save = True
                    cleared_count += 1

                # 同时清除所有小锚点（input_port）的连接映射
                if config.get('port_mappings'):
                    config['port_mappings'] = {}
                    need_save = True
                    cleared_count += 1

                # 同时清除指向其他节点的 out_connections
                if config.get('out_connections'):
                    config['out_connections'] = {}
                    need_save = True
                    cleared_count += 1

                if need_save:
                    config_path = os.path.join(node_info['path'], "config.json")
                    try:
                        with open(config_path, 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=2, ensure_ascii=False)
                        logger.info("已清除节点 %s 的监听配置及端口映射", node_name)
                    except Exception as e:
                        logger.error("保存配置失败: %s", e)

        edges_to_remove = []
        for edge in self.edges:
            target_name = None
            for name, node_item in self.nodes.items():
                if node_item == edge.end_node:
                    target_name = name
                    break
            if target_name in self.box_selected_nodes:
                edges_to_remove.append(edge)

        for edge in edges_to_remove:
            self.remove_edge(edge)

        themed_message(self, t("k_title_clear_complete"),
            t("_k_config_cleared").format(count=cleared_count), "info")
        self.clear_box_selection()

        if self.parent_window and self.parent_window.current_project_path:
            self._save_timer.stop()
            self._save_timer.start(500)

"""节点管理（组合模式，从 NodeCanvas 拆分）

职责：
- 节点增删改（add_node_to_canvas / remove_node_from_canvas / remove_node_with_cleanup）
- 节点重命名（rename_node_in_canvas）
- 清空画布（clear_canvas）
- 节点状态同步（update_node_status / sync_node_display / sync_all_nodes_display）
- 语言检测（detect_language）
- 节点操作委托（start_single_node / stop_single_node / export_node_from_canvas / stop_all_nodes）
- 节点面板（open_node_config / on_node_expand_requested）

使用方式（由 NodeCanvas __init__ 初始化）：

    self.node_mgr = NodeManager(self)
    # 调用方式：
    self.node_mgr.add_node_to_canvas(name, node_info)
    self.node_mgr.remove_node_from_canvas(name)
    ...
"""
import os
import json

from PySide6.QtGui import QPen, QColor

from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.utils.dialog_utils import themed_message
from ui.canvas.items.node_item import NodeItem


class NodeManager:
    """节点管理（增删改 / 状态同步 / 面板 / 操作委托）

    组合模式：持有对 canvas 的引用，通过 self.canvas 访问画布状态
    """

    def __init__(self, canvas):
        self.canvas = canvas

    # ── 节点增删 ──

    def add_node_to_canvas(self, node_name, node_info=None):
        """添加节点到画布

        Args:
            node_name: 节点名称
            node_info: 可选的节点信息字典（子进程模式下直接传入）
                       包含 'path', 'config', 'status' 等字段
        """
        if node_name in self.canvas.nodes:
            themed_message(
                self.canvas, t("k_title_info"), t("k_canvas_node_exists"), "info"
            )
            return

        # 获取节点信息（优先使用传入的 node_info，否则从 parent_window 读取）
        if node_info:
            # 子进程模式：直接用传入的节点信息
            language = self.detect_language(node_info.get('path', ''))
            status = node_info.get('status', 'stopped')
        elif (
            self.canvas.parent_window
            and node_name in self.canvas.parent_window.nodes_data
        ):
            # 主进程模式：从 nodes_data 读取
            parent_info = self.canvas.parent_window.nodes_data[node_name]
            language = self.detect_language(parent_info['path'])
            status = parent_info.get('status', 'stopped')
        else:
            # 兜底：默认值
            language = "Python"
            status = "stopped"

        # 计算新节点位置（避免重叠）
        if self.canvas.nodes:
            # 找到最右下角的节点位置
            max_x = max(node.pos().x() for node in self.canvas.nodes.values())
            max_y = max(node.pos().y() for node in self.canvas.nodes.values())
            x = max_x + 50
            y = max_y + 50
        else:
            # 第一个节点放在中心附近
            x = 200
            y = 150

        # 创建节点
        node = NodeItem(node_name, language, status, x, y, 140, 80, self.canvas)
        node.on_expand_requested = self.canvas.on_node_expand_requested
        self.canvas.scene.addItem(node)
        self.canvas.nodes[node_name] = node

        logger.info("节点 %s 已添加到画布 (位置: %d, %d)", node_name, x, y)

        # 自动录制命令（重放期间跳过）
        self.canvas.selection._record_create_node(node_name)

        # 触发自动保存布局（包含节点位置）
        if (
            self.canvas.parent_window
            and self.canvas.parent_window.current_project_path
        ):
            self.canvas._save_timer.stop()
            self.canvas._save_timer.start(500)

    def remove_node_from_canvas(self, node_name):
        """从画布移除节点"""
        if node_name not in self.canvas.nodes:
            return

        node = self.canvas.nodes[node_name]

        # 删除相关连线
        edges_to_remove = []
        for edge in self.canvas.edges:
            if edge.start_node == node or edge.end_node == node:
                edges_to_remove.append(edge)

        for edge in edges_to_remove:
            self.canvas.remove_edge(edge)

        # 移除节点
        self.canvas.scene.removeItem(node)
        del self.canvas.nodes[node_name]

        logger.info("节点 %s 已从画布移除", node_name)

        # 触发自动保存布局
        if (
            self.canvas.parent_window
            and self.canvas.parent_window.current_project_path
        ):
            self.canvas._save_timer.stop()
            self.canvas._save_timer.start(500)

    def remove_node_with_cleanup(self, node_name):
        """从画布删除节点并清理上下游配置"""
        if node_name not in self.canvas.nodes:
            return

        reply = themed_message(
            self.canvas,
            t("k_title_confirm_delete"),
            t("_k_canvas_remove_node_confirm").format(name=node_name),
            "question",
        )

        if not reply:
            return

        # 自动录制删除命令（需在修改前调用以收集状态）
        self.canvas.selection._record_delete_node(node_name)

        # 1. 找到所有与该节点相关的连线
        edges_to_remove = []
        upstream_nodes = set()  # 上游节点（连接到该节点的）
        downstream_nodes = set()  # 下游节点（该节点连接到的）

        for edge in self.canvas.edges:
            source_name = None
            target_name = None
            for name, node in self.canvas.nodes.items():
                if node == edge.start_node:
                    source_name = name
                if node == edge.end_node:
                    target_name = name

            if target_name == node_name:
                # 该节点是目标节点，source 是上游
                if source_name:
                    upstream_nodes.add(source_name)
                edges_to_remove.append(edge)
            elif source_name == node_name:
                # 该节点是源节点，target 是下游
                if target_name:
                    downstream_nodes.add(target_name)
                edges_to_remove.append(edge)

        # 2. 删除所有相关连线
        for edge in edges_to_remove:
            self.canvas.remove_edge(edge)

        # 3. 清除上游节点的 listen_upper_file（因为它们的下游被删除了）
        for upstream_name in upstream_nodes:
            if (
                self.canvas.parent_window
                and upstream_name in self.canvas.parent_window.nodes_data
            ):
                upstream_info = self.canvas.parent_window.nodes_data[upstream_name]
                upstream_config = upstream_info['config']
                upstream_config['listen_upper_file'] = ""

                config_path = os.path.join(upstream_info['path'], "config.json")
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(upstream_config, f, indent=2, ensure_ascii=False)
                    logger.info("已清除上游节点 %s 的监听配置", upstream_name)
                except Exception as e:
                    logger.info("[FAIL] 保存配置失败: %s", e)

        # 4. 清除下游节点的 listen_upper_file（因为上游被删除了）
        for downstream_name in downstream_nodes:
            if (
                self.canvas.parent_window
                and downstream_name in self.canvas.parent_window.nodes_data
            ):
                downstream_info = self.canvas.parent_window.nodes_data[downstream_name]
                downstream_config = downstream_info['config']
                downstream_config['listen_upper_file'] = ""

                config_path = os.path.join(downstream_info['path'], "config.json")
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(downstream_config, f, indent=2, ensure_ascii=False)
                    logger.info("已清除下游节点 %s 的监听配置", downstream_name)
                except Exception as e:
                    logger.info("[FAIL] 保存配置失败: %s", e)

        # 5. 从画布中移除节点
        node = self.canvas.nodes[node_name]
        self.canvas.scene.removeItem(node)
        del self.canvas.nodes[node_name]

        logger.info("已从画布删除节点: %s", node_name)

        # 6. 自动保存布局
        if (
            self.canvas.parent_window
            and self.canvas.parent_window.current_project_path
        ):
            self.canvas._save_timer.stop()
            self.canvas._save_timer.start(500)

    def rename_node_in_canvas(self, old_name, new_name):
        """在画布中重命名节点"""
        if old_name in self.canvas.nodes:
            node = self.canvas.nodes[old_name]
            node.node_name = new_name
            node.name_text.setPlainText(new_name)
            name_rect = node.name_text.boundingRect()
            w = node.rect().width()
            node.name_text.setPos((w - name_rect.width()) / 2, 15)

            # 更新字典键
            del self.canvas.nodes[old_name]
            self.canvas.nodes[new_name] = node

            logger.info("画布节点已重命名: %s -> %s", old_name, new_name)

    def clear_canvas(self):
        """清空画布"""
        # 移除所有连线（走 remove_edge 以清理 config.json 中的 port_mappings / listen_upper_file）
        for edge in self.canvas.edges[:]:
            self.canvas.remove_edge(edge)

        # 移除所有节点
        for node_name, node in self.canvas.nodes.items():
            self.canvas.scene.removeItem(node)
        self.canvas.nodes.clear()

        # 重置连线状态
        self.canvas.is_connecting = False
        self.canvas.connect_source = None
        if self.canvas.temp_edge:
            self.canvas.scene.removeItem(self.canvas.temp_edge)
            self.canvas.temp_edge = None

        logger.info("画布已清空")

    # ── 节点状态与显示 ──

    def update_node_status(self, node_name, status):
        """更新节点状态"""
        if node_name in self.canvas.nodes:
            self.canvas.nodes[node_name].update_status(status)

    def detect_language(self, node_path):
        """检测节点语言"""
        if os.path.exists(os.path.join(node_path, "main.py")):
            return "Python"
        elif os.path.exists(os.path.join(node_path, "main.js")):
            return "Node.js"
        elif os.path.exists(os.path.join(node_path, "main.go")):
            return "Go"
        elif os.path.exists(os.path.join(node_path, "Main.java")):
            return "Java"
        elif os.path.exists(os.path.join(node_path, "main.cpp")):
            return "C++"
        elif os.path.exists(os.path.join(node_path, "src", "main.rs")) or os.path.exists(
            os.path.join(node_path, "Cargo.toml")
        ):
            return "Rust"
        elif os.path.exists(os.path.join(node_path, "main.sh")):
            return "Shell"
        else:
            return "Unknown"

    def sync_node_display(self, node_name):
        """同步指定节点的显示（从 nodes_data 获取最新数据）"""
        if not self.canvas.parent_window or node_name not in self.canvas.nodes:
            return

        if node_name not in self.canvas.parent_window.nodes_data:
            return

        node_data = self.canvas.parent_window.nodes_data[node_name]
        config = node_data.get('config', {})
        status = node_data.get('status', 'stopped')

        node_item = self.canvas.nodes[node_name]

        display_data = {
            'name': config.get('node_name', node_name),
            'language': self.detect_language(node_data.get('path', '')),
            'status': status,
        }

        node_item.sync_with_data(display_data)

    def sync_all_nodes_display(self):
        """同步所有节点的显示"""
        for node_name in self.canvas.nodes.keys():
            self.sync_node_display(node_name)

    # ── 节点操作委托 ──

    def start_single_node(self, node_name):
        """启动单个节点（委托给父窗口）"""
        if self.canvas.parent_window:
            self.canvas.parent_window.start_selected_node_by_name(node_name)

    def stop_single_node(self, node_name):
        """停止单个节点（委托给父窗口）"""
        if self.canvas.parent_window:
            self.canvas.parent_window.stop_selected_node_by_name(node_name)

    def export_node_from_canvas(self, node_name):
        """从画布导出节点（委托给父窗口）"""
        if self.canvas.parent_window and hasattr(
            self.canvas.parent_window, 'export_node'
        ):
            self.canvas.parent_window.export_node(node_name)

    def stop_all_nodes(self):
        """停止画布上所有节点进程"""
        if (
            self.canvas.parent_window
            and hasattr(self.canvas.parent_window, 'nodes_data')
        ):
            running_nodes = [
                name
                for name, info in self.canvas.parent_window.nodes_data.items()
                if info.get('status') in ('running', 'idle')
            ]
            if running_nodes and hasattr(
                self.canvas.parent_window, '_force_stop_all_nodes'
            ):
                self.canvas.parent_window._force_stop_all_nodes(running_nodes)

    # ── 节点面板 ──

    def open_node_config(self, node_name):
        """打开节点配置对话框"""
        if (
            self.canvas.parent_window
            and node_name in self.canvas.parent_window.nodes_data
        ):
            node_info = self.canvas.parent_window.nodes_data[node_name]
            config = node_info['config']
            node_path = node_info['path']

            from ui.panels.property_panel import NodeConfigDialog

            dialog = NodeConfigDialog(node_name, config, node_path, self.canvas.parent_window)
            dialog.exec()

    def on_node_expand_requested(self, node_name):
        """节点展开按钮回调 — 以节点中心为基准展开浮动面板"""
        from ui.panels.node_expand_panel import NodeExpandPanel

        # 如果同节点已有展开面板，关闭旧的
        if hasattr(self.canvas, '_expand_panel') and self.canvas._expand_panel is not None:
            try:
                if (
                    self.canvas._expand_panel.isVisible()
                    and self.canvas._expand_panel.node_name == node_name
                ):
                    self.canvas._expand_panel._close()
            except RuntimeError:
                pass  # 面板已被销毁

        # 窗口中心与节点中心重合
        if node_name in self.canvas.nodes:
            node = self.canvas.nodes[node_name]
            scene_pos = node.pos() + node.rect().center()
            view_pos = self.canvas.mapFromScene(scene_pos)
            global_pos = self.canvas.viewport().mapToGlobal(view_pos)
            panel_w, panel_h = 620, 380
            x = global_pos.x() - panel_w // 2
            y = global_pos.y() - panel_h // 2
        else:
            x, y = 300, 200

        panel = NodeExpandPanel(node_name, self.canvas.parent_window)
        panel.move(x, y)
        panel.show()
        self.canvas._expand_panel = panel

"""
节点配置管理模块 — node_config.json 读写、轮询订阅、配置变更回调

从 node_item.py 拆分出来。
"""

from __future__ import annotations

import os

from ui.core.logger import logger


class NodeConfigManager:
    """配置管理：node_config.json 读写、轮询订阅、配置变更回调"""

    def __init__(self, node):
        self._node = node

    def get_parent_window(self):
        """获取 main_window 引用"""
        if self._node.canvas and self._node.canvas.parent_window:
            return self._node.canvas.parent_window
        return None

    def get_node_config(self):
        """获取当前节点的 config 字典（从 node_config.json + 内存运行时状态）

        配置优先级：
        1. node_config.json（磁盘）
        2. 内存运行时状态（动态更新，覆盖磁盘固定值）
        """
        pw = self.get_parent_window()
        if not pw:
            return None
        path = pw.nodes_data.get(self._node.node_name, {}).get("path", "")
        if not path:
            return None

        unified_path = os.path.join(path, "node_config.json")
        if os.path.exists(unified_path):
            return self._load_unified_config(unified_path)

        return {}

    def _load_unified_config(self, unified_path: str) -> dict:
        """加载 node_config.json（统一配置格式）"""
        import json

        try:
            with open(unified_path, encoding="utf-8") as f:
                config = json.load(f)

            # 运行时字段：用内存中的值覆盖
            pw = self.get_parent_window()
            if pw:
                mem_config = pw.nodes_data.get(self._node.node_name, {}).get("config", {})
                runtime_keys = (
                    "listen_upper_file",
                    "output_file",
                    "out_connections",
                    "filter",
                    "output_type",
                    "port_mappings",
                )
                for key in runtime_keys:
                    if key in mem_config:
                        config[key] = mem_config[key]

            return config
        except (ValueError, OSError) as e:
            logger.warning("加载 node_config.json 失败: %s", e)
            return {}

    def save_node_config(self, config: dict):
        """保存 config 到 node_config.json 并同步内存（保护元数据字段不被覆盖丢失）"""
        pw = self.get_parent_window()
        if not pw:
            return
        node_path = pw.nodes_data[self._node.node_name].get("path", "")
        if not node_path:
            return
        import json

        cfg_path = os.path.join(node_path, "node_config.json")
        saved_config = dict(config)
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, encoding="utf-8") as f:
                    disk_config = json.load(f)
                for key in ("parameters", "input_ports", "output_ports"):
                    if key in disk_config and key not in saved_config:
                        saved_config[key] = disk_config[key]
        except (ValueError, OSError):
            pass
        pw.nodes_data[self._node.node_name]["config"] = saved_config
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(saved_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning("Failed to save config for %s: %s", self._node.node_name, e)

    def on_param_changed(self, name: str, value):
        """参数变更 → 写回 node_config.json"""
        config = self.get_node_config()
        if config is not None:
            config[name] = value
            self.save_node_config(config)

    def subscribe_config_changes(self):
        """订阅 node_config.json 外部变更信号（双向数据绑定）"""
        pw = self.get_parent_window()
        if pw and hasattr(pw, "polling_manager"):
            try:
                pw.polling_manager.config_file_changed.connect(self._on_external_config_change)
            except (ValueError, OSError):
                pass  # 重复连接忽略

    def _on_external_config_change(self, node_name: str):
        """外部修改 node_config.json → 刷新画布控件"""
        if node_name != self._node.node_name:
            return
        config = self.get_node_config()
        if config:
            for name, widget in self._node._param_widgets.items():
                if name in config:
                    widget.set_value(config[name])

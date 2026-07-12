"""
节点配置管理模块 — config.json 读写、轮询订阅、配置变更回调

从 node_item.py 拆分出来。
"""

from __future__ import annotations

import os

from ui.core.logger import logger


class NodeConfigManager:
    """配置管理：config.json 读写、轮询订阅、配置变更回调"""

    def __init__(self, node):
        self._node = node

    def get_parent_window(self):
        """获取 main_window 引用"""
        if self._node.canvas and self._node.canvas.parent_window:
            return self._node.canvas.parent_window
        return None

    def get_node_config(self):
        """获取当前节点的 config 字典（支持 node_config.json + 向后兼容）

        配置优先级：
        1. node_config.json（新格式）
        2. config.json + start.json（旧格式，向后兼容）
        3. 内存运行时状态（动态更新）

        解决配置文件分离导致的元数据丢失问题，支持统一配置格式。
        """
        pw = self.get_parent_window()
        if not pw:
            return None
        path = pw.nodes_data.get(self._node.node_name, {}).get("path", "")
        if not path:
            return None

        # 尝试加载 node_config.json（新格式）
        unified_path = os.path.join(path, "node_config.json")
        if os.path.exists(unified_path):
            return self._load_unified_config(unified_path)

        # 向后兼容：加载 config.json + start.json
        return self._load_legacy_config(path)

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

    def _load_legacy_config(self, path: str) -> dict:
        """加载旧格式配置（config.json + start.json）"""
        import json

        # 加载 config.json
        cfg_path = os.path.join(path, "config.json")
        config = {}
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, encoding="utf-8") as f:
                    config = json.load(f)
        except (ValueError, OSError) as e:
            logger.warning("加载 config.json 失败: %s", e)

        # 合并 start.json（向后兼容）
        start_path = os.path.join(path, "start.json")
        if os.path.exists(start_path):
            try:
                with open(start_path, encoding="utf-8") as f:
                    start_config = json.load(f)

                # 处理 start.json 的多节点格式
                if "nodes" in start_config and isinstance(start_config["nodes"], list):
                    for node in start_config["nodes"]:
                        if node.get("name") == config.get("node_name"):
                            # 合并启动配置
                            config.update(
                                {"entry": node.get("entry", "listener.py"), "python_exe": node.get("python_exe", "")}
                            )

                            # 合并运行时配置
                            if "config" in node:
                                config.update(node["config"])
                            break

                # 处理单节点格式
                elif start_config.get("name") == config.get("node_name"):
                    config.update(
                        {
                            "entry": start_config.get("entry", "listener.py"),
                            "python_exe": start_config.get("python_exe", ""),
                        }
                    )
                    if "config" in start_config:
                        config.update(start_config["config"])

            except (ValueError, OSError) as e:
                logger.warning("加载 start.json 失败: %s", e)

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

    def save_node_config(self, config: dict):
        """保存 config 到文件并同步内存（保护 parameters/input_ports 不被覆盖丢失）

        解决 start.json 启动覆盖导致元数据丢失后，保存回来的 config 不含
        parameters/input_ports，再次加载时无法构建面板的问题。
        """
        pw = self.get_parent_window()
        if not pw:
            return
        node_path = pw.nodes_data[self._node.node_name].get("path", "")
        if not node_path:
            return
        import json

        cfg_path = os.path.join(node_path, "config.json")
        # 从磁盘加载完整 config（保护 parameters/input_ports 等元数据）
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
        """参数变更 → 写回 config.json"""
        config = self.get_node_config()
        if config is not None:
            config[name] = value
            self.save_node_config(config)

    def subscribe_config_changes(self):
        """订阅 config.json 外部变更信号（双向数据绑定）"""
        pw = self.get_parent_window()
        if pw and hasattr(pw, "polling_manager"):
            try:
                pw.polling_manager.config_file_changed.connect(self._on_external_config_change)
            except (ValueError, OSError):
                pass  # 重复连接忽略

    def _on_external_config_change(self, node_name: str):
        """外部修改 config.json → 刷新画布控件"""
        if node_name != self._node.node_name:
            return
        config = self.get_node_config()
        if config:
            for name, widget in self._node._param_widgets.items():
                if name in config:
                    widget.set_value(config[name])

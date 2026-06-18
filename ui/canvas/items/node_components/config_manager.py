"""
节点配置管理模块 — config.json 读写、轮询订阅、配置变更回调

从 node_item.py 拆分出来。
"""
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
        """获取当前节点的 config 字典（合并磁盘 config.json + 内存运行时状态）

        解决 start.json 启动时整体替换 node_info['config'] 导致 parameters/input_ports
        元数据丢失的问题——始终从磁盘加载完整 config.json，仅对运行时字段
        （listen_upper_file/output_file/out_connections 等）用内存值覆盖。
        """
        pw = self.get_parent_window()
        if not pw:
            return None
        path = pw.nodes_data.get(self._node.node_name, {}).get('path', '')
        if not path:
            return None
        # 从磁盘加载完整 config.json（始终包含 parameters/input_ports）
        cfg_path = os.path.join(path, 'config.json')
        merged = {}
        try:
            if os.path.exists(cfg_path):
                import json
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    merged = json.load(f)
        except Exception:
            pass
        # 运行时字段：用内存中的值覆盖（这些值是执行过程中动态更新的）
        mem_config = pw.nodes_data.get(self._node.node_name, {}).get('config', {})
        for key in ('listen_upper_file', 'output_file', 'out_connections',
                     'filter', 'output_type', 'port_mappings'):
            if key in mem_config:
                merged[key] = mem_config[key]
        return merged

    def save_node_config(self, config: dict):
        """保存 config 到文件并同步内存（保护 parameters/input_ports 不被覆盖丢失）

        解决 start.json 启动覆盖导致元数据丢失后，保存回来的 config 不含
        parameters/input_ports，再次加载时无法构建面板的问题。
        """
        pw = self.get_parent_window()
        if not pw:
            return
        node_path = pw.nodes_data[self._node.node_name].get('path', '')
        if not node_path:
            return
        import json
        cfg_path = os.path.join(node_path, 'config.json')
        # 从磁盘加载完整 config（保护 parameters/input_ports 等元数据）
        saved_config = dict(config)
        try:
            if os.path.exists(cfg_path):
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    disk_config = json.load(f)
                for key in ('parameters', 'input_ports', 'output_ports'):
                    if key in disk_config and key not in saved_config:
                        saved_config[key] = disk_config[key]
        except Exception:
            pass
        pw.nodes_data[self._node.node_name]['config'] = saved_config
        try:
            with open(cfg_path, 'w', encoding='utf-8') as f:
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
        if pw and hasattr(pw, 'polling_manager'):
            try:
                pw.polling_manager.config_file_changed.connect(
                    self._on_external_config_change)
            except Exception:
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

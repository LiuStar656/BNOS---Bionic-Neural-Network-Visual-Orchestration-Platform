"""
NodeDataProvider - 节点数据提供者协议

定义统一的数据访问接口，实现 RegularNodeProvider 和 CompositeNodeProvider 来适配不同类型的节点。
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path


class NodeDataProvider(ABC):
    """节点数据提供者协议"""

    @abstractmethod
    def get_node_name(self) -> str:
        """获取节点名称"""
        pass

    @abstractmethod
    def get_node_path(self) -> Path:
        """获取节点路径"""
        pass

    @abstractmethod
    def get_config_path(self) -> Path:
        """获取配置文件路径"""
        pass

    @abstractmethod
    def get_output_path(self) -> Path:
        """获取输出文件路径"""
        pass

    @abstractmethod
    def get_log_dir(self) -> Path:
        """获取日志目录"""
        pass

    @abstractmethod
    def get_status(self) -> str:
        """获取节点状态 (running/idle/stopped)"""
        pass

    @abstractmethod
    def get_resource_limits(self) -> dict:
        """获取资源限制配置"""
        pass

    @abstractmethod
    def start(self):
        """启动节点"""
        pass

    @abstractmethod
    def stop(self):
        """停止节点"""
        pass

    @abstractmethod
    def is_composite(self) -> bool:
        """是否为复合节点"""
        pass

    def get_composite_config_path(self) -> Path | None:
        """获取 composite.json 路径（仅复合节点）"""
        return None

    def get_pipeline_path(self) -> Path | None:
        """获取 pipeline.json 路径（仅复合节点）"""
        return None

    def get_dag_status(self) -> dict | None:
        """获取 DAG 状态（仅复合节点）"""
        return None

    def get_sub_nodes(self) -> list[str]:
        """获取子节点列表（仅复合节点）"""
        return []


class RegularNodeProvider(NodeDataProvider):
    """普通节点数据提供者"""

    def __init__(self, node_name: str, node_info: dict, parent_window):
        self._node_name = node_name
        self._node_info = node_info
        self._parent_window = parent_window
        self._node_path = Path(node_info.get("path", ""))

    def get_node_name(self) -> str:
        return self._node_name

    def get_node_path(self) -> Path:
        return self._node_path

    def get_config_path(self) -> Path:
        from ui.core.config.config_merger import get_config_path

        return Path(get_config_path(str(self._node_path)))

    def get_output_path(self) -> Path:
        return self._node_path / "output.json"

    def get_log_dir(self) -> Path:
        return self._node_path / "logs"

    def get_status(self) -> str:
        return self._node_info.get("status", "stopped")

    def get_resource_limits(self) -> dict:
        config = self._node_info.get("config", {})
        return config.get("resource_limit", {})

    def start(self):
        if self._parent_window:
            self._parent_window.start_selected_node_by_name(self._node_name)

    def stop(self):
        if self._parent_window:
            self._parent_window.stop_selected_node_by_name(self._node_name)

    def is_composite(self) -> bool:
        return False


class CompositeNodeProvider(NodeDataProvider):
    """复合节点数据提供者"""

    def __init__(self, comp_id: str, parent_window):
        self._comp_id = comp_id
        self._parent_window = parent_window
        self._project_path = getattr(parent_window, "current_project_path", "") if parent_window else ""
        self._mgr = None
        if parent_window and hasattr(parent_window, "canvas"):
            self._mgr = getattr(parent_window.canvas, "_composite_manager", None)

    def get_node_name(self) -> str:
        return self._comp_id

    def get_node_path(self) -> Path:
        from ui.core.node.composite_node import CompositeNode

        return CompositeNode._comp_config_dir(self._project_path, self._comp_id)

    def get_config_path(self) -> Path:
        from ui.core.node.composite_node import CompositeNode

        return CompositeNode._comp_config_path(self._project_path, self._comp_id)

    def get_output_path(self) -> Path:
        from ui.core.node.composite_node import CompositeNode

        return CompositeNode._comp_output_dir(self._project_path, self._comp_id) / "output.json"

    def get_log_dir(self) -> Path:
        from ui.core.node.composite_node import CompositeNode

        return CompositeNode._comp_logs_dir(self._project_path, self._comp_id)

    def get_status(self) -> str:
        if self._parent_window and hasattr(self._parent_window, "nodes_data"):
            return self._parent_window.nodes_data.get(self._comp_id, {}).get("status", "stopped")
        if self._mgr and self._mgr.is_running(self._comp_id):
            return "running"
        return "stopped"

    def get_resource_limits(self) -> dict:
        return {}

    def start(self):
        if self._parent_window:
            self._parent_window.start_selected_node_by_name(self._comp_id)

    def stop(self):
        if self._parent_window:
            self._parent_window.stop_selected_node_by_name(self._comp_id)

    def is_composite(self) -> bool:
        return True

    def get_composite_config_path(self) -> Path | None:
        return self.get_config_path()

    def get_pipeline_path(self) -> Path | None:
        from ui.core.node.composite_node import CompositeNode

        return CompositeNode._comp_pipeline_path(self._project_path, self._comp_id)

    def get_dag_status(self) -> dict | None:
        from ui.core.node.composite_node import CompositeNode

        status_path = CompositeNode._comp_config_dir(self._project_path, self._comp_id) / "status.json"
        if status_path.exists():
            try:
                return json.loads(status_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return None

    def get_sub_nodes(self) -> list[str]:
        if self._mgr:
            return self._mgr.get_nodes(self._comp_id)
        return []

    def get_display_name(self) -> str:
        """获取复合节点的展示名称"""
        if self._mgr:
            comp = self._mgr._composites.get(self._comp_id, {})
            return comp.get("display_name") or self._comp_id
        return self._comp_id

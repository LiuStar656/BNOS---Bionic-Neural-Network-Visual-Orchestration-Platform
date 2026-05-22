"""
节点注册表组件 (NodeRegistry)

记录每一个节点的名称和路径，在GUI重启时作为辅助数据源。
工作流程：
  1. GUI 启动/打开项目时，先扫描项目 nodes/ 目录下的 config.json（主要数据源）
  2. 再读取 node_registry.json 注册表文件（辅助数据源）
  3. 以扫描结果为最高优先，注册表为辅助参考
  4. 每次扫描结束后自动同步注册表，保持数据一致性
"""
import os
import json
from datetime import datetime
from typing import Dict, Optional


class NodeRegistry:
    """节点注册表组件
    
    持久化文件：<project_path>/node_registry.json
    数据结构：
    {
        "nodes": {
            "node_name": {
                "path": "/absolute/path/to/node",
                "last_seen": "2025-01-01T00:00:00",
                "status": "active"  // "active" | "missing"
            }
        },
        "updated_at": "2025-01-01T00:00:00"
    }
    """

    REGISTRY_FILENAME = "node_registry.json"

    def __init__(self, project_path: str):
        """初始化注册表
        
        Args:
            project_path: 项目根目录的绝对路径
        """
        self._project_path = os.path.abspath(project_path)
        self._registry_path = os.path.join(self._project_path, self.REGISTRY_FILENAME)
        self._nodes: Dict[str, dict] = {}
        self._project_path_normalized = os.path.normpath(self._project_path)

    # ---- 属性 ----
    @property
    def file_path(self) -> str:
        """注册表文件的完整路径"""
        return self._registry_path

    @property
    def node_count(self) -> int:
        """已注册节点总数"""
        return len(self._nodes)

    @property
    def active_count(self) -> int:
        """活跃节点数（目录存在）"""
        return sum(1 for v in self._nodes.values() if v.get("status") == "active")

    @property
    def missing_count(self) -> int:
        """缺失节点数（目录不存在）"""
        return sum(1 for v in self._nodes.values() if v.get("status") == "missing")

    # ---- 持久化 ----
    def load(self) -> bool:
        """从注册表文件加载数据
        
        Returns:
            True 加载成功，False 文件不存在或加载失败
        """
        if not os.path.exists(self._registry_path):
            return False
        try:
            with open(self._registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._nodes = data.get("nodes", {})
            return True
        except (json.JSONDecodeError, IOError):
            self._nodes = {}
            return False

    def save(self) -> bool:
        """保存注册表数据到文件
        
        Returns:
            True 保存成功，False 保存失败
        """
        try:
            data = {
                "nodes": self._nodes,
                "updated_at": datetime.now().isoformat()
            }
            os.makedirs(os.path.dirname(self._registry_path), exist_ok=True)
            with open(self._registry_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except IOError:
            return False

    # ---- 节点注册/注销 ----
    def register_node(self, node_name: str, node_path: str, mount_root: str = None):
        """注册或更新单个节点
        
        Args:
            node_name: 节点名称（来自 config.json 的 node_name 字段）
            node_path: 节点目录的绝对路径
            mount_root: 挂载根目录路径（外部挂载节点），None 表示本地节点
        """
        abs_path = os.path.abspath(node_path)
        entry = {
            "path": abs_path,
            "last_seen": datetime.now().isoformat(),
            "status": "active" if os.path.isdir(abs_path) else "missing"
        }
        if mount_root:
            entry["mount_root"] = os.path.abspath(mount_root)
        else:
            # 保留已有的 mount_root（如果存在）
            existing = self._nodes.get(node_name, {})
            if "mount_root" in existing:
                entry["mount_root"] = existing["mount_root"]
        self._nodes[node_name] = entry

    def unregister_node(self, node_name: str):
        """从注册表中移除指定节点
        
        Args:
            node_name: 要移除的节点名称
        """
        self._nodes.pop(node_name, None)

    # ---- 扫描同步（核心方法）----
    def sync_from_scan(self, scan_results: Dict[str, str]):
        """以扫描结果为准，同步更新注册表。
        
        这是整个注册表组件的核心方法，遵循「扫描优先、注册表辅助」原则：
        1. 扫描到的节点 → 标记为 active，更新路径和时间戳
        2. 扫描不到但在注册表中的节点 → 标记为 missing（保留历史记录）
        3. 外部挂载节点不受同步影响（保持原有 mount_root 和 status）
        
        Args:
            scan_results: {node_name: node_absolute_path}，来源于 nodes/ 目录扫描结果
        """
        # 1. 扫描到的节点：全部注册/更新为活跃状态
        for name, path in scan_results.items():
            existing = self._nodes.get(name, {})
            mount_root = existing.get("mount_root")
            self.register_node(name, path, mount_root=mount_root)

        # 2. 注册表里有但扫描不到的节点：仅标记本地节点为 missing，挂载节点保持不变
        registered_names = set(self._nodes.keys())
        scanned_names = set(scan_results.keys())
        for name in registered_names - scanned_names:
            info = self._nodes[name]
            if info.get("status") == "active" and not info.get("mount_root"):
                self._nodes[name]["status"] = "missing"

    # ---- 查询接口 ----
    def get_all_nodes(self) -> Dict[str, dict]:
        """获取所有已注册节点的信息（包含 active 和 missing）"""
        return dict(self._nodes)

    def get_node_info(self, node_name: str) -> Optional[dict]:
        """获取单个节点的注册信息
        
        Args:
            node_name: 节点名称
        
        Returns:
            节点信息字典，或 None（未注册）
        """
        return self._nodes.get(node_name)

    def get_active_nodes(self) -> Dict[str, dict]:
        """获取所有活跃节点（目录确实存在的节点）"""
        return {k: v for k, v in self._nodes.items() if v.get("status") == "active"}

    def get_missing_nodes(self) -> Dict[str, dict]:
        """获取所有缺失节点（注册过但目录已不存在的节点）"""
        return {k: v for k, v in self._nodes.items() if v.get("status") == "missing"}

    def is_registered(self, node_name: str) -> bool:
        """检查节点是否在注册表中"""
        return node_name in self._nodes

    def is_active(self, node_name: str) -> bool:
        """检查节点是否处于活跃状态"""
        info = self._nodes.get(node_name)
        return info is not None and info.get("status") == "active"

    def is_missing(self, node_name: str) -> bool:
        """检查节点是否处于缺失状态"""
        info = self._nodes.get(node_name)
        return info is not None and info.get("status") == "missing"

    # ---- 挂载节点查询 ----
    def is_mounted(self, node_name: str) -> bool:
        """检查节点是否为外部挂载节点"""
        info = self._nodes.get(node_name)
        return info is not None and bool(info.get("mount_root"))

    def get_mount_root(self, node_name: str) -> Optional[str]:
        """获取节点的挂载根目录路径
        
        Returns:
            挂载根目录路径或 None（本地节点）
        """
        info = self._nodes.get(node_name)
        return info.get("mount_root") if info else None

    def get_mounted_nodes(self) -> Dict[str, dict]:
        """获取所有外部挂载节点"""
        return {k: v for k, v in self._nodes.items() if v.get("mount_root")}

    def get_nodes_by_mount_root(self, mount_root: str) -> Dict[str, dict]:
        """获取指定挂载根目录下的所有节点
        
        Args:
            mount_root: 挂载根目录路径
        """
        mount_root_norm = os.path.normpath(os.path.abspath(mount_root))
        return {k: v for k, v in self._nodes.items()
                if v.get("mount_root") and os.path.normpath(v["mount_root"]) == mount_root_norm}

    # ---- 维护 ----
    def clear(self):
        """清空注册表（不删除文件，仅清空内存数据）"""
        self._nodes = {}

    def purge_missing(self):
        """清除所有 missing 状态的节点记录"""
        self._nodes = {k: v for k, v in self._nodes.items() if v.get("status") != "missing"}

    def delete_file(self):
        """删除注册表文件"""
        if os.path.exists(self._registry_path):
            os.remove(self._registry_path)

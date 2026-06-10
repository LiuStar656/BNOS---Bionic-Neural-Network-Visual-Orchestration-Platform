"""
连接关系反推器 - 通过节点的 config.json 反推连线关系

核心功能：
1. 扫描所有节点的 config.json，解析 listen_upper_file 字段
2. 从上游路径中提取节点名称，重建 source → target 连线关系
3. 与现有 canvas_layout.json 对比，返回新增/冲突/孤立信息
4. 支持多种路径格式（绝对路径、相对路径、跨平台路径）
"""

import os
import re
import json
import logging
from ui.core.i18n import t
from typing import Dict, List, Tuple, Optional, Set

logger = logging.getLogger(__name__)


class ConnectionInferrer:
    """通过 config.json 反推节点间连线关系"""

    def __init__(self, project_path: str, nodes_data: Dict[str, dict]):
        """
        Args:
            project_path: 项目根目录的绝对路径
            nodes_data: 主窗口的 nodes_data 字典，格式:
                {node_name: {'config': {...}, 'path': '...', 'process': ..., 'status': '...'}}
        """
        self.project_path = os.path.abspath(project_path)
        self.nodes_data = nodes_data

    # ──────────────────── 公共 API ────────────────────

    def infer_all_edges(self) -> List[dict]:
        """
        扫描所有节点 config.json，反推全部连线关系。

        扫描来源：
          - listen_upper_file → target_port=None（默认大锚点）
          - port_mappings → target_port=端口名（小锚点）

        Returns:
            [{"source": "上游节点名", "target": "下游节点名", "target_port": None|"prompt"|...}, ...]
            未找到有效 upstream 的节点不出现在结果中。
        """
        edges = []
        for node_name, node_info in self.nodes_data.items():
            config = node_info.get("config", {})
            # 1) listen_upper_file → 默认锚点
            listen_file = config.get("listen_upper_file", "")
            if listen_file and listen_file.strip():
                upstream = self._extract_node_name_from_path(
                    listen_file.strip().replace("\\", "/"))
                if upstream:
                    edges.append({"source": upstream, "target": node_name, "target_port": None})

            # 2) port_mappings → 小锚点
            port_maps = config.get("port_mappings", {})
            if isinstance(port_maps, dict):
                for port_name, path in port_maps.items():
                    if not path or not isinstance(path, str):
                        continue
                    upstream = self._extract_node_name_from_path(
                        path.strip().replace("\\", "/"))
                    if upstream:
                        edges.append({
                            "source": upstream,
                            "target": node_name,
                            "target_port": port_name,
                        })
        return edges

    def compare_with_existing(self, existing_edges: List[dict]) -> dict:
        """
        与现有连线对比，返回差异分析。

        Args:
            existing_edges: canvas_layout.json 中已有的 edges 列表
                [{"source": "A", "target": "B"}, ...]

        Returns:
            {
                "inferred": [...],       # 从 config 推断的全部连线
                "existing": [...],       # 已有的连线
                "new": [...],            # 新增连线（config 有但 canvas 没有）
                "missing": [...],        # 已有但 config 中无对应 listen_upper_file 的连线
                "conflicts": [...],      # 冲突连线（同一 target 但 source 不同）
                "orphans": [...],        # 无上游连接的节点（config 中 listen_upper_file 为空）
                "stats": {               # 统计信息
                    "total_inferred": int,
                    "total_existing": int,
                    "new_count": int,
                    "missing_count": int,
                    "conflict_count": int,
                    "orphan_count": int
                }
            }
        """
        inferred = self.infer_all_edges()

        # 构建查找索引：{target: source}
        inferred_map = {e["target"]: e["source"] for e in inferred}
        existing_map = {e["target"]: e["source"] for e in existing_edges}

        # 新增：config 中有但 canvas 中没有
        new_edges = [
            e for e in inferred
            if e["target"] not in existing_map
        ]

        # 缺失：canvas 中有但 config 中没有（可能连线已被删除或手动修改了 config）
        missing_edges = [
            e for e in existing_edges
            if e["target"] not in inferred_map
        ]

        # 冲突：同一 target，但 source 不同
        conflicts = []
        for e in inferred:
            target = e["target"]
            if target in existing_map and existing_map[target] != e["source"]:
                conflicts.append({
                    "target": target,
                    "inferred_source": e["source"],
                    "existing_source": existing_map[target]
                })

        # 孤立节点：config 中 listen_upper_file 为空或无效
        orphans = []
        for node_name, node_info in self.nodes_data.items():
            config = node_info.get("config", {})
            listen_file = config.get("listen_upper_file", "")
            if not listen_file or not listen_file.strip():
                orphans.append(node_name)

        return {
            "inferred": inferred,
            "existing": existing_edges,
            "new": new_edges,
            "missing": missing_edges,
            "conflicts": conflicts,
            "orphans": orphans,
            "stats": {
                "total_inferred": len(inferred),
                "total_existing": len(existing_edges),
                "new_count": len(new_edges),
                "missing_count": len(missing_edges),
                "conflict_count": len(conflicts),
                "orphan_count": len(orphans),
            }
        }

    def get_node_upstream(self, node_name: str) -> Optional[str]:
        """获取单个节点的上游节点名称"""
        node_info = self.nodes_data.get(node_name)
        if not node_info:
            return None
        return self._get_upstream_node_name(node_name, node_info)

    def get_node_downstreams(self, node_name: str) -> List[str]:
        """获取监听某个节点的所有下游节点列表"""
        downstreams = []
        for other_name, other_info in self.nodes_data.items():
            if other_name == node_name:
                continue
            upstream = self._get_upstream_node_name(other_name, other_info)
            if upstream == node_name:
                downstreams.append(other_name)
        return downstreams

    # ──────────────────── 内部方法 ────────────────────

    def _get_upstream_node_name(self, node_name: str, node_info: dict) -> Optional[str]:
        """
        从节点的 config.json 的 listen_upper_file 中提取上游节点名称。

        支持的路径格式：
          - 绝对路径: F:/project/nodes/node_A/output.json
          - 相对路径: ../node_A/output.json
          - 混合路径: ../data/upper_data.json（无明确节点，返回 None）
          - Windows 路径: C:\\project\\nodes\\node_A\\output.json
          - 空字符串/"": 返回 None
        """
        config = node_info.get("config", {})
        listen_file = config.get("listen_upper_file", "")

        if not listen_file or not listen_file.strip():
            return None

        listen_file = listen_file.strip()

        # 标准化路径分隔符
        normalized = listen_file.replace("\\", "/")

        # 尝试从路径中提取节点名
        # 路径格式通常为: .../nodes/<node_name>/output.json
        upstream = self._extract_node_name_from_path(normalized)
        if upstream:
            logger.debug(f"[Inferrer] {node_name} → upstream: {upstream} (from '{listen_file}')")
            return upstream

        logger.debug(f"[Inferrer] {node_name}: unable to extract upstream from '{listen_file}'")
        return None

    def _extract_node_name_from_path(self, path: str) -> Optional[str]:
        """
        从 listen_upper_file 路径中提取上游节点名称。

        支持的格式：
          - 标准格式: .../nodes/<node_name>/output.json → 提取 node_name
          - 简写格式: ../node_name/output.json → 提取 node_name
          - 非 nodes 目录下的路径: 尝试兜底匹配已知节点名

        Returns:
            节点名称，或 None（无法提取）
        """
        # 去除文件名，只保留目录路径
        dir_path = os.path.dirname(path)

        # 取最后一级目录名作为候选节点名
        candidate = os.path.basename(dir_path)

        # 验证候选名称是否在已知节点列表中
        if candidate in self.nodes_data:
            return candidate

        # 尝试从路径中匹配 nodes/<xxx>/ 模式
        # 例如: /project/nodes/my_node/output.json → my_node
        nodes_pattern = re.search(r'/nodes/([^/]+)', path)
        if nodes_pattern:
            name = nodes_pattern.group(1)
            if name in self.nodes_data:
                return name

        # 最后尝试：在路径的所有目录层级中查找已知节点名
        parts = dir_path.split("/")
        for part in reversed(parts):
            if part in self.nodes_data:
                return part

        return None

    # ──────────────────── 诊断工具 ────────────────────

    def diagnose(self) -> str:
        """生成诊断报告，显示所有节点的 listen_upper_file 解析情况"""
        lines = []
        lines.append("=" * 60)
        lines.append("连线反推诊断报告")
        lines.append("=" * 60)
        lines.append(f"项目路径: {self.project_path}")
        lines.append(f"节点总数: {len(self.nodes_data)}")
        lines.append("")

        for node_name, node_info in self.nodes_data.items():
            config = node_info.get("config", {})
            listen_file = config.get("listen_upper_file", "")
            upstream = self._get_upstream_node_name(node_name, node_info)

            lines.append(f"节点: {node_name}")
            lines.append(f"  listen_upper_file: '{listen_file}'")
            if upstream:
                lines.append(f"  → 上游节点: {upstream}")
            elif listen_file and listen_file.strip():
                lines.append(f"  → 无法解析上游节点（路径可能不在 nodes/ 目录下）")
            else:
                lines.append(f"  → 无上游连接（孤立节点）")
            lines.append("")

        # 汇总
        inferred = self.infer_all_edges()
        lines.append("-" * 60)
        lines.append(f"推断连线数: {len(inferred)}")
        for edge in inferred:
            lines.append(f"  {edge['source']} → {edge['target']}")

        lines.append("=" * 60)
        return "\n".join(lines)

"""
ui/core/composite_node.py
复合节点管理 — 压缩/解耦/运行时切换 / DAG / 持久化。

环境管理 → ui.core.composite_env
编排器生成 → ui.core.composite_orchestrator

与 NodeGroupManager 联动：
  - 压缩 → 自动创建节点组 + 锁定（防止用户手动移出节点）
  - 解耦 → 自动解锁 + 删除节点组
"""
import os
import json
import uuid
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, QThread, Signal

from ui.core.logger import logger
from ui.core.i18n.i18n import t
from ui.core.i18n.translation_keys import TK
from ui.core.node.composite_orchestrator import render_orchestrator_script
from ui.core.node.composite_env import (
    comp_venv_path,
    get_python_exe,
    merge_requirements,
    remove_comp_env,
)
from ui.core.node.language_detector import LanguageDetector

# ── 与 NodeGroupManager 的绑定规则 ──
# 复合节点组命名: __composite__{comp_id}
# 颜色: #4ec9b0（青绿色，匹配复合节点边框）
# 自动锁定: 压缩后 lock_group，防止用户手动移出节点
# 解耦时: unlock_group → delete_group
# 用户手动创建的节点组（无 __composite__ 前缀）不受影响

GROUP_PREFIX = "__composite__"
GROUP_COLOR = "#4ec9b0"


class CompositeNode:
    """
    复合节点：将多个原始节点包装为单个运行时单元。
    自动与 NodeGroupManager 联动：压缩 → 创建节点组，解耦 → 删除节点组。

    存储格式 (node_clusters.json):
    {
      "composites": {
        "composite_1": {
          "nodes": ["node_python_prompt", "node_python_llm", "node_python_json_parser"],
          "runtime": "inprocess",
          "group_name": "__composite__composite_1",
          "canvas_position": {"x": 100, "y": 200},
          "original_positions": {
            "node_python_prompt": {"x": 100, "y": 200},
          }
        }
      }
    }
    """

    GROUP_PREFIX = GROUP_PREFIX
    GROUP_COLOR = GROUP_COLOR

    def __init__(self, project_path: str, canvas=None, group_manager=None):
        self._project_path = project_path
        self._canvas = canvas
        self._group_manager = group_manager
        self._composites: Dict[str, dict] = {}
        self._config_path = os.path.join(project_path, "node_clusters.json")
        self._active_processes: Dict[str, subprocess.Popen] = {}
        self.load()

    # ── 持久化 ──

    def load(self):
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._composites = json.load(f).get("composites", {})
                # Auto-collapse any expanded composites from previous session
                for comp_id, comp in list(self._composites.items()):
                    if comp.get("_expanded"):
                        comp["_expanded"] = False
                        if "_drag_anchor_positions" in comp:
                            del comp["_drag_anchor_positions"]
            except Exception as e:
                logger.warning("加载 node_clusters.json 失败: %s", e)
                self._composites = {}

    def save(self):
        """Atomic write to node_clusters.json (immediate, not debounced).
        Uses retry logic to handle transient file locks (antivirus, indexing)."""
        if getattr(self, '_saving', False):
            return  # Concurrent save already in progress

        import time
        self._saving = True
        try:
            data = {"composites": self._composites}
            tmp_path = self._config_path + ".tmp"

            # Write to temp file
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Atomic replace with retry for Windows file lock issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    os.replace(tmp_path, self._config_path)
                    break
                except PermissionError:
                    if attempt < max_retries - 1:
                        time.sleep(0.1 * (attempt + 1))
                    else:
                        # Last resort: delete target then rename
                        try:
                            os.remove(self._config_path)
                            os.replace(tmp_path, self._config_path)
                        except Exception:
                            logger.error("save: cannot write %s after %d retries",
                                         self._config_path, max_retries)
                except OSError as e:
                    logger.error("save: OS error on %s: %s", self._config_path, e)
                    break
        finally:
            self._saving = False

    # ── 复合节点端口路由（_port_routing）──
    # 路由信息存储在 node_clusters.json 的每个 composite 的 _port_routing 字段中，
    # 而非内部节点的 config.json。这样 listen_upper_file 保持为空，端口识别不受影响。
    #
    # _port_routing 数据结构：
    # {
    #     "input": {
    #         "port_name": {"source_output_path": "nodes/xxx/output.json"}
    #     },
    #     "output": {
    #         "port_name": {
    #             "target_composite": "composite_xxx",  # 可为 null（外部节点）
    #             "target_node": "internal_name",
    #             "target_port": "port_name"
    #         }
    #     }
    # }
    # ──

    def _ensure_port_routing(self, comp_id: str):
        """确保 _port_routing 字段存在。"""
        comp = self._composites.get(comp_id, {})
        if "_port_routing" not in comp:
            comp["_port_routing"] = {"input": {}, "output": {}}

    def _get_port_routing(self, comp_id: str) -> dict:
        """获取复合节点的端口路由。"""
        comp = self._composites.get(comp_id, {})
        return comp.get("_port_routing", {"input": {}, "output": {}})

    def set_input_routing(self, comp_id: str, port_name: str, source_output_path: str):
        """记录输入端口的路由：上游 output.json → 本复合节点的入口。"""
        comp = self._composites.get(comp_id)
        if not comp:
            return
        self._ensure_port_routing(comp_id)
        comp["_port_routing"]["input"][port_name] = {
            "source_output_path": source_output_path
        }
        self.save_debounced()

    def set_output_routing(self, comp_id: str, port_name: str,
                           target_composite: str | None,
                           target_node: str, target_port: str):
        """记录输出端口的路由：本复合节点的输出 → 下游节点。"""
        comp = self._composites.get(comp_id)
        if not comp:
            return
        self._ensure_port_routing(comp_id)
        comp["_port_routing"]["output"][port_name] = {
            "target_composite": target_composite,
            "target_node": target_node,
            "target_port": target_port,
        }
        self.save_debounced()

    def clear_input_routing(self, comp_id: str, port_name: str):
        """清除输入端口路由记录。"""
        comp = self._composites.get(comp_id, {})
        routing = comp.get("_port_routing", {}).get("input", {})
        if port_name in routing:
            del routing[port_name]
            self.save_debounced()

    def clear_output_routing(self, comp_id: str, port_name: str):
        """清除输出端口路由记录。"""
        comp = self._composites.get(comp_id, {})
        routing = comp.get("_port_routing", {}).get("output", {})
        if port_name in routing:
            del routing[port_name]
            self.save_debounced()

    # ── 持久化（续）──

    def save_debounced(self):
        """Debounced version: delays write until no further calls for 500ms.
        Used by itemChange during drag to avoid disk I/O spam (60fps)."""
        from PySide6.QtCore import QTimer
        if not hasattr(self, '_save_timer'):
            self._save_timer = QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self.save)
        self._save_timer.stop()
        self._save_timer.start(500)

    # ── Port Identification ──

    def _identify_ports(self, node_names: list, edges_list: list,
                         nodes_data: dict) -> dict:
        """Identify input and output ports for a composite node.

        Input port (exactly one): the node whose listen_upper_file is empty
            AND has in-degree 0 (no internal upstream).

        Output ports (one per DAG leaf): internal nodes with out-degree 0.

        Returns:
            {"input_ports": [{...}], "output_ports": [{...}]}
        """
        node_set = set(node_names)

        # Build in-degree and out-degree from internal edges
        in_degree = {n: 0 for n in node_names}
        out_degree = {n: 0 for n in node_names}
        for e in edges_list:
            if e.get("from") in node_set and e.get("to") in node_set:
                out_degree[e["from"]] += 1
                in_degree[e["to"]] += 1

        # Input port: first node with in_degree 0 and empty listen_upper_file
        input_ports = []
        for n in node_names:
            if in_degree[n] == 0:
                nd = nodes_data.get(n, {})
                config = nd.get('config', {})
                listen = config.get('listen_upper_file', '')
                if not listen:
                    input_ports.append({
                        "internal_node": n,
                        "type": "input",
                        "port_name": f"{n}_in",
                        "display_name": n,
                    })
                    break  # Only one input port

        # Output ports: all DAG leaf nodes (out_degree 0)
        output_ports = []
        for n in node_names:
            if out_degree[n] == 0:
                output_ports.append({
                    "internal_node": n,
                    "type": "output",
                    "port_name": f"{n}_out",
                    "display_name": n,
                })

        return {
            "input_ports": input_ports,
            "output_ports": output_ports,
        }

    def _validate_dag_single_entry(self, node_names: list, edges_list: list,
                                    nodes_data: dict) -> Tuple[bool, str]:
        """Validate DAG has exactly one entry node (in_degree==0, empty listen_upper_file).

        防错机制：复合节点必须为单入口 DAG（A→B→C 或 A→B 同时 A→C）。
        多入口 DAG（如 A→C 且 B→C）不允许创建或折叠。

        Returns:
            (is_valid, error_message)
        """
        in_degree = {n: 0 for n in node_names}
        for e in edges_list:
            if e.get("from") in node_names and e.get("to") in node_names:
                in_degree[e["to"]] += 1

        candidates = []
        for n in node_names:
            if in_degree[n] == 0:
                nd = nodes_data.get(n, {})
                config = nd.get('config', {})
                if not config.get('listen_upper_file', ''):
                    candidates.append(n)

        if len(candidates) == 0:
            return False, t(TK._COMPOSITE_NO_ENTRY)
        if len(candidates) > 1:
            return False, t(TK._COMPOSITE_MULTI_ENTRY).format(
                count=len(candidates), nodes=", ".join(candidates))
        return True, ""

    def get_ports(self, comp_id: str) -> dict:
        """Get input/output ports for a composite node."""
        c = self._composites.get(comp_id, {})
        return {
            "input_ports": c.get("input_ports", []),
            "output_ports": c.get("output_ports", []),
        }

    # ── Expand / Collapse ──

    def cleanup_all_expanded(self):
        """Collapse all expanded composites. Call on project close or switch."""
        for comp_id, comp in list(self._composites.items()):
            if comp.get("_expanded"):
                comp_item = self._canvas.nodes.get(comp_id) if self._canvas else None
                if comp_item:
                    try:
                        self._collapse_composite(comp_id, comp_item)
                    except Exception as e:
                        logger.warning("cleanup_all_expanded: collapse %s failed: %s", comp_id, e)
                else:
                    # Frame might still exist, clean it up
                    frame_key = f"__frame__{comp_id}"
                    frame = (self._canvas.nodes or {}).pop(frame_key, None)
                    if frame and frame.scene():
                        frame.scene().removeItem(frame)
                    # Ensure internal nodes are hidden
                    for n in comp.get("nodes", []):
                        item = (self._canvas.nodes or {}).get(n)
                        if item:
                            item.setVisible(False)
                    comp["_expanded"] = False
                    self.save()

    def toggle_expand(self, comp_id: str):
        """Toggle expand/collapse for a composite node on the canvas."""
        if not self._canvas:
            return

        comp_item = self._canvas.nodes.get(comp_id)
        if not comp_item:
            # May have been removed externally
            return

        comp = self._composites.get(comp_id)
        if not comp:
            return

        if comp.get("_expanded", False):
            self._collapse_composite(comp_id, comp_item)
        else:
            self._expand_composite(comp_id, comp_item)

    def _expand_composite(self, comp_id: str, comp_item):
        """Expand composite: hide item, show internal nodes, draw group frame."""
        comp = self._composites.get(comp_id)
        if not comp:
            return

        # Guard: already expanded
        if comp.get("_expanded"):
            return

        # Guard: composite item must exist on canvas
        if comp_item.scene() is None:
            return

        node_names = comp.get("nodes", [])
        if not node_names:
            return

        # Guard: check all internal node items still exist on canvas
        for n in node_names:
            if n not in self._canvas.nodes:
                logger.warning("_expand_composite: internal node %s missing from canvas", n)
                return
        positions = comp.get("original_positions", {})
        comp_pos = comp.get("canvas_position", {"x": 0, "y": 0})

        comp_item.setVisible(False)
        comp_item.is_expanded = True

        # Morph composite-connected edges into internal-node edges
        self._morph_composite_to_internal_edges(comp_id, comp_item, node_names)

        # 批量定位内部节点（抑制逐节点连线刷新，避免抖动）
        self._canvas._batch_updating = True
        try:
            child_items = []
            for n in node_names:
                item = self._canvas.nodes.get(n)
                if item:
                    pos = positions.get(n, {"x": 0, "y": 0})
                    item.setPos(
                        comp_pos.get("x", 0) + pos.get("x", 0),
                        comp_pos.get("y", 0) + pos.get("y", 0)
                    )
                    item.setVisible(True)
                    child_items.append(item)
        finally:
            self._canvas._batch_updating = False

        # 批量更新所有内部节点的连线路径（一次到位，无抖动）
        self._batch_update_edges_for_nodes(node_names)

        # Restore internal edges that were hidden during compression
        for info in comp.get("_internal_edges", []):
            for edge in self._canvas.edges:
                src_name = edge.start_node.node_name if hasattr(edge.start_node, 'node_name') else ''
                tgt_name = edge.end_node.node_name if hasattr(edge.end_node, 'node_name') else ''
                if src_name == info["src"] and tgt_name == info["tgt"]:
                    edge.setVisible(True)
                    edge.update_path()
                    break

        from ui.canvas.items.composite_group_frame import CompositeGroupFrame
        frame = CompositeGroupFrame(
            comp_id=comp_id,
            display_name=comp.get("display_name", ""),
            child_items=child_items,
            composite_manager=self,
        )
        self._canvas.scene.addItem(frame)
        self._canvas.nodes[f"__frame__{comp_id}"] = frame

        # Store expanded state
        comp["_expanded"] = True
        comp["_child_items"] = node_names
        self.save()

    def _collapse_composite(self, comp_id: str, comp_item):
        """Collapse composite: hide internal nodes, remove frame, show composite item."""
        comp = self._composites.get(comp_id)
        if not comp:
            return

        node_names = comp.get("nodes", [])

        # ── 防错：展开态单入口 DAG 校验 ──
        # 当用户在展开时重新编排了内部连线，可能导致多入口 DAG，
        # 此时应拒绝折叠并提示用户修正。
        node_set = set(node_names)
        edges_list = []
        for edge_item in self._canvas.edges:
            src = edge_item.start_node.node_name if hasattr(edge_item.start_node, 'node_name') else ''
            tgt = edge_item.end_node.node_name if hasattr(edge_item.end_node, 'node_name') else ''
            if src in node_set and tgt in node_set:
                edges_list.append({"from": src, "to": tgt})
        nodes_data = self._canvas.parent_window.nodes_data if self._canvas.parent_window else {}
        is_valid, err_msg = self._validate_dag_single_entry(node_names, edges_list, nodes_data)
        if not is_valid:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                None,
                t(TK.COMPOSITE_COLLAPSE_BLOCKED_TITLE),
                err_msg
            )
            logger.warning("collapse blocked for %s: %s", comp_id, err_msg)
            return

        # Save current positions back to original_positions
        comp_pos = comp.get("canvas_position", {"x": 0, "y": 0})
        for n in node_names:
            item = self._canvas.nodes.get(n)
            if item and item.isVisible():
                comp["original_positions"][n] = {
                    "x": item.pos().x() - comp_pos.get("x", 0),
                    "y": item.pos().y() - comp_pos.get("y", 0)
                }
                item.setVisible(False)

        # Hide internal edges again (they will be managed by composite DAG)
        node_set = set(node_names)
        internal_edge_info = []
        for edge in self._canvas.edges:
            src_name = edge.start_node.node_name if hasattr(edge.start_node, 'node_name') else ''
            tgt_name = edge.end_node.node_name if hasattr(edge.end_node, 'node_name') else ''
            if src_name in node_set and tgt_name in node_set:
                if edge.isVisible():
                    internal_edge_info.append({
                        "src": src_name,
                        "tgt": tgt_name,
                        "src_port": getattr(edge, 'source_port_name', ''),
                        "tgt_port": getattr(edge, 'target_port_name', ''),
                    })
                edge.setVisible(False)
        comp["_internal_edges"] = internal_edge_info

        # Remove group frame
        frame_key = f"__frame__{comp_id}"
        frame = self._canvas.nodes.pop(frame_key, None)
        if frame and frame.scene():
            frame.scene().removeItem(frame)

        # Show composite item
        comp_item.setVisible(True)
        comp_item.is_expanded = False

        # Reverse morph: internal-node edges back to composite edges
        self._morph_internal_to_composite_edges(comp_id, comp_item, node_names)

        # Refresh ports (in case connections changed while expanded)
        self._refresh_ports_on_collapse(comp_id, comp_item, node_names)

        comp["_expanded"] = False
        self.save()

    def _refresh_ports_on_collapse(self, comp_id, comp_item, node_names):
        """Re-identify ports after collapse to reflect any changed connections.

        Also re-binds all composite-connected edges to the new anchors
        (since update_ports() destroys old anchors). Edges whose port_name
        no longer matches any new port are removed.
        """
        node_set = set(node_names)
        edges_list = []
        for edge_item in self._canvas.edges:
            src = edge_item.start_node.node_name if hasattr(edge_item.start_node, 'node_name') else ''
            tgt = edge_item.end_node.node_name if hasattr(edge_item.end_node, 'node_name') else ''
            if src in node_set and tgt in node_set:
                edges_list.append({"from": src, "to": tgt})

        # Save composite-connected edges before anchor destruction
        saved_edges = []
        for edge in list(self._canvas.edges):
            if edge.start_node is comp_item:
                port_name = getattr(getattr(edge, '_source_anchor', None), 'port_name', '')
                saved_edges.append({"edge": edge, "direction": "output", "port_name": port_name})
            elif edge.end_node is comp_item:
                port_name = getattr(getattr(edge, '_target_anchor', None), 'port_name', '')
                saved_edges.append({"edge": edge, "direction": "input", "port_name": port_name})

        nodes_data = self._canvas.parent_window.nodes_data if self._canvas.parent_window else {}
        new_ports = self._identify_ports(node_names, edges_list, nodes_data)

        comp = self._composites.get(comp_id)
        if comp:
            comp["input_ports"] = new_ports.get("input_ports", [])
            comp["output_ports"] = new_ports.get("output_ports", [])

        comp_item.update_ports(
            new_ports.get("input_ports", []),
            new_ports.get("output_ports", [])
        )

        # Re-bind saved edges to new anchors (or remove if port no longer exists)
        for info in saved_edges:
            edge = info["edge"]
            if info["direction"] == "output":
                new_anchor = comp_item.find_anchor_by_port(info["port_name"], "output")
                if new_anchor:
                    edge._source_anchor = new_anchor
                    edge.update_path()
                else:
                    # Port removed — remove the edge
                    if edge in self._canvas.edges:
                        self._canvas.edges.remove(edge)
                    if edge.scene():
                        edge.scene().removeItem(edge)
                    logger.info("collapse: removed stale output edge %s (port %s gone)",
                                getattr(edge, 'edge_id', ''), info["port_name"])
            else:
                new_anchor = comp_item.find_anchor_by_port(info["port_name"], "input")
                if new_anchor:
                    edge._target_anchor = new_anchor
                    edge.update_path()
                else:
                    if edge in self._canvas.edges:
                        self._canvas.edges.remove(edge)
                    if edge.scene():
                        edge.scene().removeItem(edge)
                    logger.info("collapse: removed stale input edge %s (port %s gone)",
                                getattr(edge, 'edge_id', ''), info["port_name"])

        # ── Clean up stale _port_routing entries ──
        # When internal node changes (e.g. receiver replaced), old port names
        # may no longer exist. Remove _port_routing entries for dead ports.
        valid_input_ports = {p["port_name"] for p in new_ports.get("input_ports", [])}
        valid_output_ports = {p["port_name"] for p in new_ports.get("output_ports", [])}
        routing = self._get_port_routing(comp_id)
        stale_inputs = [p for p in routing.get("input", {}) if p not in valid_input_ports]
        stale_outputs = [p for p in routing.get("output", {}) if p not in valid_output_ports]
        for port_name in stale_inputs:
            self.clear_input_routing(comp_id, port_name)
            logger.info("collapse: cleaned stale _port_routing input[%s] (port no longer exists)", port_name)
        for port_name in stale_outputs:
            self.clear_output_routing(comp_id, port_name)
            logger.info("collapse: cleaned stale _port_routing output[%s] (port no longer exists)", port_name)

    def _batch_update_edges_for_nodes(self, node_names: list):
        """批量更新指定节点所有连线的路径（展开/折叠后一次到位，避免抖动）。"""
        node_set = set(node_names)
        updated = set()
        for edge in self._canvas.edges:
            if edge in updated:
                continue
            src_name = edge.start_node.node_name if hasattr(edge.start_node, 'node_name') else ''
            tgt_name = edge.end_node.node_name if hasattr(edge.end_node, 'node_name') else ''
            if src_name in node_set or tgt_name in node_set:
                if edge._waypoints and not isinstance(edge._waypoints[0], tuple):
                    edge._sync_abs_to_rel()
                edge.update_path()
                updated.add(edge)

    def _hide_composite_edges(self, comp_id: str):
        """Hide all edges connected to a composite node item."""
        from PySide6.QtCore import Qt
        comp_item = self._canvas.nodes.get(comp_id) if self._canvas else None
        if not comp_item:
            return
        for edge in self._canvas.edges:
            if edge.start_node is comp_item or edge.end_node is comp_item:
                edge.setVisible(False)
                edge.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def _show_composite_edges(self, comp_id: str):
        """Restore visibility of edges connected to a composite node item."""
        from PySide6.QtCore import Qt
        comp_item = self._canvas.nodes.get(comp_id) if self._canvas else None
        if not comp_item:
            return
        for edge in self._canvas.edges:
            if edge.start_node is comp_item or edge.end_node is comp_item:
                edge.setVisible(True)
                edge.setAcceptedMouseButtons(
                    Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
                )

    def _hide_internal_external_edges(self, comp_id: str, node_names: list):
        """Hide edges where one endpoint is internal and the other is external."""
        from PySide6.QtCore import Qt
        if not self._canvas:
            return
        node_set = set(node_names)
        # Store for restoration
        self._composites.setdefault(comp_id, {})["_hidden_external_edges"] = []
        hidden = self._composites[comp_id]["_hidden_external_edges"]
        for edge in self._canvas.edges:
            src_name = edge.start_node.node_name if hasattr(edge.start_node, 'node_name') else ''
            tgt_name = edge.end_node.node_name if hasattr(edge.end_node, 'node_name') else ''
            src_in = src_name in node_set
            tgt_in = tgt_name in node_set
            if src_in != tgt_in:  # One inside, one outside
                # Store edge info for restoration
                hidden.append({
                    "src": src_name,
                    "tgt": tgt_name,
                    "src_port": getattr(edge, 'source_port_name', ''),
                    "tgt_port": getattr(edge, 'target_port_name', ''),
                })
                edge.setVisible(False)
                edge.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def _show_internal_external_edges(self, comp_id: str, node_names: list):
        """Restore visibility of internal↔external edges.
        Skips edges where the external endpoint belongs to another currently-expanded composite."""
        from PySide6.QtCore import Qt
        if not self._canvas:
            return
        comp = self._composites.get(comp_id, {})
        hidden_info = comp.get("_hidden_external_edges", [])
        node_set = set(node_names)

        # Find all other expanded composites at this moment
        other_protected = set()  # node names protected by other expanded composites
        for cid, cdata in self._composites.items():
            if cid == comp_id:
                continue
            if cdata.get("_expanded"):
                other_protected.update(cdata.get("nodes", []))

        for info in hidden_info:
            # Determine which endpoint is "external"
            external_name = info["tgt"] if info["src"] in node_set else info["src"]
            # Skip if the external node is protected by another expanded composite
            if external_name in other_protected:
                continue
            for edge in self._canvas.edges:
                src_name = edge.start_node.node_name if hasattr(edge.start_node, 'node_name') else ''
                tgt_name = edge.end_node.node_name if hasattr(edge.end_node, 'node_name') else ''
                if src_name == info["src"] and tgt_name == info["tgt"]:
                    edge.setVisible(True)
                    edge.setAcceptedMouseButtons(
                        Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton
                    )
                    break
        comp["_hidden_external_edges"] = []

    # ── Edge morphing (expand ↔ collapse) ──

    def _morph_composite_to_internal_edges(self, comp_id: str, comp_item,
                                           node_names: list):
        """During expand: turn composite↔external edges into internal_node↔external edges.

        For each output port "node_b_out" → internal "node_b":
            edge [external → composite_output_anchor("node_b_out")] becomes
            edge [external → internal_node_item("node_b")]

        For each input port "node_a_in" → internal "node_a":
            edge [composite_input_anchor("node_a_in") → external] becomes
            edge [internal_node_item("node_a") → external]
        """
        from PySide6.QtCore import Qt
        from ui.canvas.items.edge_item import EdgeItem

        comp = self._composites.get(comp_id, {})
        port_to_internal = {}
        for p in comp.get("input_ports", []):
            port_to_internal[p["port_name"]] = p["internal_node"]
        for p in comp.get("output_ports", []):
            port_to_internal[p["port_name"]] = p["internal_node"]

        morphed = []

        for edge in list(self._canvas.edges):
            # External node → composite input anchor
            if edge.end_node is comp_item:
                tgt_anchor = getattr(edge, '_target_anchor', None)
                port_name = getattr(tgt_anchor, 'port_name', '')
                internal_name = port_to_internal.get(port_name)
                if internal_name:
                    internal_item = self._canvas.nodes.get(internal_name)
                    if internal_item:
                        edge.setVisible(False)
                        edge.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                        temp = EdgeItem(
                            edge.start_node, internal_item, self._canvas,
                            target_anchor=internal_item.input_anchor,
                            source_anchor=getattr(edge, '_source_anchor', None),
                        )
                        self._canvas.scene.addItem(temp)
                        self._canvas.edges.append(temp)
                        temp.update_path()
                        morphed.append({"original": edge, "temp": temp})

            # Composite output anchor → external node
            elif edge.start_node is comp_item:
                src_anchor = getattr(edge, '_source_anchor', None)
                port_name = getattr(src_anchor, 'port_name', '')
                internal_name = port_to_internal.get(port_name)
                if internal_name:
                    internal_item = self._canvas.nodes.get(internal_name)
                    if internal_item:
                        edge.setVisible(False)
                        edge.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                        temp = EdgeItem(
                            internal_item, edge.end_node, self._canvas,
                            target_anchor=getattr(edge, '_target_anchor', None),
                            source_anchor=internal_item.output_anchor,
                        )
                        self._canvas.scene.addItem(temp)
                        self._canvas.edges.append(temp)
                        temp.update_path()
                        morphed.append({"original": edge, "temp": temp})

        comp["_morphed_edges"] = morphed

        # ── Sync config.json for expanded state ──
        self._sync_configs_for_expand(comp_id, node_names, port_to_internal)

    def _morph_internal_to_composite_edges(self, comp_id: str, comp_item,
                                           node_names: list):
        """During collapse: remove temporary internal-node edges and show
        original composite-connected edges. Handles new edges added while expanded."""
        from PySide6.QtCore import Qt
        comp = self._composites.get(comp_id, {})
        morphed = comp.get("_morphed_edges", [])

        node_set = set(node_names)

        for m in morphed:
            original = m["original"]
            temp = m["temp"]
            # Remove temp edge
            try:
                if temp in self._canvas.edges:
                    self._canvas.edges.remove(temp)
            except ValueError:
                pass
            if temp.scene():
                temp.scene().removeItem(temp)
            # Show original composite edge
            original.setVisible(True)
            original.setAcceptedMouseButtons(
                Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)
            original.update_path()

        # Hide any NEW internal↔external edges added while expanded
        # (these will be captured as ports by _refresh_ports_on_collapse)
        for edge in self._canvas.edges:
            src_name = edge.start_node.node_name if hasattr(edge.start_node, 'node_name') else ''
            tgt_name = edge.end_node.node_name if hasattr(edge.end_node, 'node_name') else ''
            if (src_name in node_set) != (tgt_name in node_set):
                if edge.isVisible():
                    edge.setVisible(False)
                    edge.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        comp["_morphed_edges"] = []

        # ── Sync config.json for collapsed state ──
        self._sync_configs_for_collapse(comp_id, node_names)

    # ── Config sync on expand / collapse ──

    def _sync_configs_for_expand(self, comp_id: str, node_names: list, port_to_internal: dict):
        """On expand: update internal node configs to reflect direct external connections.

        Two-phase approach:
        1. Scan canvas edges (handles temp edges created by morph)
        2. Read from _port_routing (handles connections made while collapsed)

        - For each internal node that IS an input port target:
          set listen_upper_file → external source's output.json
        - For each internal node that IS an output port source:
          add out_connections entry → external target
        """
        import json as _json
        node_set = set(node_names)
        nodes_dir = os.path.join(self._project_path, "nodes")
        if not self._canvas:
            return

        # Build map: internal_name → external_infos
        in_conns: Dict[str, list] = {}  # internal_name → [{source_name, source_path, port_name}]
        out_conns: Dict[str, list] = {}  # internal_name → [{target_name, target_port, port_name}]

        for edge in self._canvas.edges:
            if not edge.isVisible():
                continue
            src = edge.start_node
            tgt = edge.end_node
            if src is None or tgt is None:
                continue
            src_name = src.node_name if hasattr(src, 'node_name') else ''
            tgt_name = tgt.node_name if hasattr(tgt, 'node_name') else ''
            if not src_name or not tgt_name:
                continue

            # External → internal (input direction)
            if src_name not in node_set and tgt_name in node_set:
                port_name = getattr(getattr(edge, '_target_anchor', None), 'port_name', '') or 'default'
                src_path = os.path.abspath(os.path.join(nodes_dir, src_name, "output.json"))
                in_conns.setdefault(tgt_name, []).append({
                    "source_name": src_name,
                    "source_path": src_path,
                    "port_name": port_name,
                })

            # Internal → external (output direction)
            if src_name in node_set and tgt_name not in node_set:
                port_name = getattr(getattr(edge, '_source_anchor', None), 'port_name', '') or 'default'
                tgt_port = getattr(getattr(edge, '_target_anchor', None), 'port_name', '') or 'default'
                out_conns.setdefault(src_name, []).append({
                    "target_name": tgt_name,
                    "target_port": tgt_port,
                    "port_name": port_name,
                })

        # ── Phase 2: also read from _port_routing ──
        routing = self._get_port_routing(comp_id)
        for port_name, route in routing.get("input", {}).items():
            internal_name = port_to_internal.get(port_name)
            if internal_name and internal_name in node_set:
                src_path = route.get("source_output_path", "")
                if src_path:
                    in_conns.setdefault(internal_name, []).append({
                        "source_name": self._extract_node_from_path(src_path) or "external",
                        "source_path": src_path,
                        "port_name": port_name,
                    })
        for port_name, route in routing.get("output", {}).items():
            internal_name = port_to_internal.get(port_name)
            if internal_name and internal_name in node_set:
                tgt_node = route.get("target_node", "")
                tgt_port = route.get("target_port", "default")
                if tgt_node:
                    out_conns.setdefault(internal_name, []).append({
                        "target_name": tgt_node,
                        "target_port": tgt_port,
                        "port_name": port_name,
                    })

        # Apply input connections
        for internal_name, entries in in_conns.items():
            config_path = os.path.join(nodes_dir, internal_name, "config.json")
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = _json.load(f)
            except Exception:
                cfg = {}
            cfg['listen_upper_file'] = entries[0]["source_path"]
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    _json.dump(cfg, f, indent=2, ensure_ascii=False)
                logger.info("expand sync: %s listen_upper_file → %s",
                            internal_name, entries[0]["source_path"])
            except Exception as e:
                logger.error("expand sync %s: %s", internal_name, e)

        # Apply output connections
        for internal_name, entries in out_conns.items():
            config_path = os.path.join(nodes_dir, internal_name, "config.json")
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = _json.load(f)
            except Exception:
                cfg = {}
            cfg.setdefault('out_connections', {})
            for entry in entries:
                cfg['out_connections'][entry["port_name"]] = f"{entry['target_name']}|{entry['target_port']}"
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    _json.dump(cfg, f, indent=2, ensure_ascii=False)
                logger.info("expand sync: %s out_connections updated: %s",
                            internal_name, list(cfg['out_connections'].keys()))
            except Exception as e:
                logger.error("expand sync %s: %s", internal_name, e)

    def _sync_configs_for_collapse(self, comp_id: str, node_names: list):
        """On collapse: sync external refs back to _port_routing, then clear internal configs.

        Phase 1: Read external connections from internal node configs → write to _port_routing
        Phase 2: Clear listen_upper_file / out_connections pointing outside the composite
        """
        import json as _json
        node_set = set(node_names)
        nodes_dir = os.path.join(self._project_path, "nodes")

        # Build reverse mapping: internal_node → (port_name, port_type)
        comp = self._composites.get(comp_id, {})
        internal_to_input_port = {}
        internal_to_output_port = {}
        for p in comp.get("input_ports", []):
            internal_to_input_port[p.get("internal_node", "")] = p.get("port_name", "")
        for p in comp.get("output_ports", []):
            internal_to_output_port[p.get("internal_node", "")] = p.get("port_name", "")

        # ── Phase 1: sync external refs back to _port_routing ──
        for node_name in node_names:
            config_path = os.path.join(nodes_dir, node_name, "config.json")
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = _json.load(f)
            except Exception:
                continue

            # Input direction: listen_upper_file pointing externally
            listen = cfg.get('listen_upper_file', '')
            if listen:
                upstream = self._extract_node_from_path(listen)
                if upstream and upstream not in node_set:
                    port_name = internal_to_input_port.get(node_name, "")
                    if port_name:
                        self.set_input_routing(comp_id, port_name, listen)
                        logger.info("collapse sync: _port_routing input[%s] ← %s (from %s)",
                                    port_name, listen, node_name)

            # Output direction: out_connections pointing externally
            out_conns = cfg.get('out_connections', {})
            for port_key, target in out_conns.items():
                if isinstance(target, str) and target:
                    ext_node = target.split('|')[0]
                    if ext_node and ext_node not in node_set:
                        tgt_port = target.split('|')[1] if '|' in target else 'default'
                        port_name = internal_to_output_port.get(node_name, "")
                        if port_name:
                            self.set_output_routing(comp_id, port_name, None, ext_node, tgt_port)
                            logger.info("collapse sync: _port_routing output[%s] → %s|%s (from %s)",
                                        port_name, ext_node, tgt_port, node_name)

        # ── Phase 2: clear external refs from internal configs ──
        for node_name in node_names:
            config_path = os.path.join(nodes_dir, node_name, "config.json")
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = _json.load(f)
            except Exception:
                continue

            changed = False

            # Clear listen_upper_file if it points externally
            listen = cfg.get('listen_upper_file', '')
            if listen:
                upstream = self._extract_node_from_path(listen)
                if upstream and upstream not in node_set:
                    cfg['listen_upper_file'] = ''
                    changed = True
                    logger.info("collapse sync: %s listen_upper_file cleared (was → %s)", node_name, upstream)

            # Remove out_connections entries pointing externally
            out_conns = cfg.get('out_connections', {})
            to_remove = []
            for port_key, target in list(out_conns.items()):
                ext_node = target.split('|')[0] if isinstance(target, str) else ''
                if ext_node and ext_node not in node_set:
                    to_remove.append(port_key)
            for port_key in to_remove:
                del out_conns[port_key]
                changed = True
                logger.info("collapse sync: %s out_connections[%s] removed (was → external)", node_name, port_key)

            if changed:
                try:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        _json.dump(cfg, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    logger.error("collapse sync %s: %s", node_name, e)

    @staticmethod
    def _extract_node_from_path(file_path: str) -> Optional[str]:
        """Extract a node name from a file path like .../nodes/<name>/output.json."""
        if not file_path:
            return None
        import re
        normalized = file_path.replace('\\', '/')
        m = re.search(r'/nodes/([^/]+)', normalized)
        if m:
            return m.group(1)
        m = re.search(r'\.\./([^/]+)/output\.json', normalized)
        if m:
            return m.group(1)
        return None

    # ── 核心操作 ──

    def compress(self, node_names: list, name: str = "") -> Tuple[bool, str, Optional[str]]:
        """
        将多个节点压缩为复合节点。

        Phase 1 (sync, fast): validation, ID generation, port identification
        Phase 2 (async, background thread): merge_requirements (venv/requirements I/O)
        Phase 3 (on thread finish, main thread): canvas operations + save

        返回: (成功, 消息, 复合节点ID)
        """
        if not self._canvas:
            return False, t(TK.COMPOSITE_CANVAS_UNAVAILABLE), None

        # Normalize to plain list (handles SelectedNodesList and other custom iterables)
        node_names = list(node_names)

        # ── Phase 1: Synchronous validation ──

        if len(node_names) < 2:
            return False, t(TK.COMPOSITE_NEED_2_NODES), None

        for n in node_names:
            if n in self._composites:
                return False, t(TK._COMPOSITE_IS_ITSELF).format(name=n), None
            existing = self._find_composite_of_node(n)
            if existing:
                return False, t(TK._COMPOSITE_ALREADY_IN).format(name=n, composite=existing), None
            if n not in self._canvas.nodes:
                return False, t(TK._COMPOSITE_NOT_ON_CANVAS).format(name=n), None
            if self._canvas.parent_window:
                node_data = self._canvas.parent_window.nodes_data.get(n, {})
                status = node_data.get('status', '')
                if status in ('running', 'idle', 'starting', 'stopping'):
                    return False, t(TK._COMPOSITE_RUNNING).format(name=n, status=status), None

        # Language compatibility check
        node_paths_map = {}
        for n in node_names:
            node_data = self._canvas.parent_window.nodes_data.get(n, {}) if self._canvas.parent_window else {}
            node_path = node_data.get('path', '')
            if not node_path:
                node_path = os.path.join(self._project_path, "nodes", n)
            node_paths_map[n] = node_path
        common_lang = LanguageDetector.detect_multi(list(node_paths_map.values()))
        if common_lang == "Unknown":
            unknown_nodes = [n for n, p in node_paths_map.items() if LanguageDetector.detect(p) == "Unknown"]
            return False, t(TK.COMPOSITE_UNKNOWN_LANGUAGE).format(nodes=", ".join(unknown_nodes)), None
        if "|" in common_lang:
            node_langs = {n: LanguageDetector.detect(p) for n, p in node_paths_map.items()}
            lang_summary = {}
            for n, l in node_langs.items():
                lang_summary.setdefault(l, []).append(n)
            msg_parts = [f"{lang}({'/'.join(names)})" for lang, names in lang_summary.items()]
            return False, t(TK.COMPOSITE_LANGUAGE_MISMATCH).format(details=" | ".join(msg_parts)), None

        # DAG cycle detection
        node_set = set(node_names)
        edges_list = []
        for edge_item in self._canvas.edges:
            src = edge_item.start_node.node_name if hasattr(edge_item.start_node, 'node_name') else ''
            tgt = edge_item.end_node.node_name if hasattr(edge_item.end_node, 'node_name') else ''
            if src in node_set and tgt in node_set:
                edges_list.append({"from": src, "to": tgt})
        cycle_nodes = self._has_cycle(node_set, edges_list)
        if cycle_nodes:
            return False, t(TK.COMPOSITE_CIRCULAR_DEPS).format(nodes=", ".join(sorted(cycle_nodes))), None

        if len(node_names) > 1 and edges_list:
            connected = set()
            for e in edges_list:
                connected.add(e["from"])
                connected.add(e["to"])
            isolated = node_set - connected
            if isolated:
                logger.warning("以下节点在压缩集内无连线: %s", isolated)

        # ── Pre-compute data for Phase 3 (canvas ops) ──
        comp_id = f"composite_{uuid.uuid4().hex[:8]}"
        display_name = name.strip() if name and name.strip() else ""
        nodes_data = self._canvas.parent_window.nodes_data if self._canvas.parent_window else {}

        original_positions = {}
        for n in node_names:
            item = self._canvas.nodes.get(n)
            if item:
                original_positions[n] = {"x": item.pos().x(), "y": item.pos().y()}

        if original_positions:
            cx = sum(p["x"] for p in original_positions.values()) / len(original_positions)
            cy = sum(p["y"] for p in original_positions.values()) / len(original_positions)
        else:
            cx, cy = 0, 0

        ports = self._identify_ports(node_names, edges_list, nodes_data)

        # ── 防错：单入口 DAG 校验 ──
        is_valid, err_msg = self._validate_dag_single_entry(node_names, edges_list, nodes_data)
        if not is_valid:
            return False, err_msg, None

        # ── Phase 2: Launch background thread for heavy I/O ──
        worker = _CompressWorker(
            self._project_path,
            comp_id,
            display_name,
            node_names,
            nodes_data,
        )
        # Store Phase 3 data for the callback
        worker._compress_data = {
            "comp_id": comp_id,
            "node_names": node_names,
            "cx": cx,
            "cy": cy,
            "display_name": display_name,
            "ports": ports,
            "original_positions": original_positions,
            "common_lang": common_lang,
        }
        worker.finished.connect(lambda: self._on_compress_worker_done(worker))
        worker.start()

        return True, t(TK._COMPOSITE_COMPRESSED).format(n=len(node_names)), comp_id

    def _on_compress_worker_done(self, worker):
        """Callback from background thread — run canvas ops on main thread."""
        data = worker._compress_data

        ok = worker._merge_ok
        msg = worker._merge_msg

        if not ok:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(
                None,
                "Composite Env Failed",
                f"Failed to set up composite environment:\n{msg}"
            )
            return

        # Phase 3: Canvas operations (must run on main thread — Qt rule)
        comp_id = data["comp_id"]
        node_names = data["node_names"]
        cx = data["cx"]
        cy = data["cy"]
        display_name = data["display_name"]
        ports = data["ports"]
        original_positions = data["original_positions"]
        common_lang = data["common_lang"]

        # NodeGroupManager integration
        group_name = f"{GROUP_PREFIX}{comp_id}"
        if self._group_manager:
            self._detach_from_user_groups(node_names)
            self._group_manager.create_group(group_name, color=GROUP_COLOR)
            self._group_manager.add_nodes_to_group(group_name, node_names)
            self._group_manager.lock_group(group_name)

        # Store
        self._composites[comp_id] = {
            "nodes": node_names,
            "runtime": "inprocess",
            "group_name": group_name,
            "display_name": display_name,
            "canvas_position": {"x": cx, "y": cy},
            "original_positions": original_positions,
            "input_ports": ports.get("input_ports", []),
            "output_ports": ports.get("output_ports", []),
            "language": common_lang if common_lang != "Unknown" else "Python",
        }
        self.save()

        # Canvas
        self._canvas_compress(comp_id, node_names, cx, cy, display_name, ports)

    def decompress(self, comp_id: str) -> Tuple[bool, str]:
        """
        解耦复合节点为独立节点。

        步骤:
          1. 停止复合节点（如果在运行）
          2. 从画布移除复合节点，显示原始节点，还原位置
          3. 删除 NodeGroupManager 中的同名节点组
          4. 清除持久化
        """
        comp = self._composites.get(comp_id)
        if not comp:
            return False, t(TK.COMPOSITE_NOT_FOUND)

        # Auto-collapse if expanded (clean up frame + show composite item)
        if comp.get("_expanded"):
            comp_item = self._canvas.nodes.get(comp_id) if self._canvas else None
            if comp_item:
                self._collapse_composite(comp_id, comp_item)

        node_names = comp["nodes"]
        original_positions = comp.get("original_positions", {})
        group_name = comp.get("group_name", "")

        # 停止运行中的复合节点
        self._stop_if_running(comp_id)

        # 画布操作: 恢复原始节点
        self._canvas_decompress(comp_id, node_names, original_positions)

        # 删除节点组
        if group_name and self._group_manager:
            try:
                self._group_manager.unlock_group(group_name)
            except Exception:
                pass
            try:
                self._group_manager.delete_group(group_name)
            except Exception:
                pass

        # 清除
        del self._composites[comp_id]
        self.save()

        # 清理 orchestrator 和复合节点 venv
        orch_path = os.path.join(self._project_path, f"orchestrator_{comp_id}.py")
        try:
            os.remove(orch_path)
        except OSError:
            pass

        remove_comp_env(self._project_path, comp_id,
                        comp.get("display_name", ""), logger)

        return True, t(TK._COMPOSITE_DECOMPRESSED).format(n=len(node_names))

    def set_runtime(self, comp_id: str, mode: str) -> Tuple[bool, str]:
        """切换运行时模式。"""
        if comp_id not in self._composites:
            return False, t(TK.COMPOSITE_NOT_FOUND)
        if mode not in ("process", "inprocess"):
            return False, t(TK.COMPOSITE_INVALID_MODE).format(mode=mode)
        # S04: 运行时禁止切换模式
        if self.is_running(comp_id):
            return False, t(TK.COMPOSITE_RUNNING_CANNOT_SWITCH)
        self._composites[comp_id]["runtime"] = mode
        self.save()
        return True, t(TK._COMPOSITE_MODE_SET).format(mode=mode)

    def get_runtime(self, comp_id: str) -> Optional[str]:
        c = self._composites.get(comp_id)
        return c.get("runtime") if c else None

    def get_nodes(self, comp_id: str) -> List[str]:
        c = self._composites.get(comp_id)
        return list(c["nodes"]) if c else []

    def get_all_composites(self) -> Dict[str, dict]:
        return dict(self._composites)

    def get_node_count(self, comp_id: str) -> int:
        return len(self.get_nodes(comp_id))

    # ── DAG ──

    def get_dag(self, comp_id: str) -> List[dict]:
        """推导复合节点内部的 DAG（原画布连线）。"""
        node_set = set(self.get_nodes(comp_id))
        if not self._canvas:
            return []
        edges_list = []
        for edge_item in self._canvas.edges:
            src = edge_item.start_node.node_name if hasattr(edge_item.start_node, 'node_name') else ''
            tgt = edge_item.end_node.node_name if hasattr(edge_item.end_node, 'node_name') else ''
            if src in node_set and tgt in node_set:
                edges_list.append({
                    "from": src,
                    "to": tgt,
                    "source_port": getattr(edge_item, 'source_port_name', '') or '',
                    "target_port": getattr(edge_item, 'target_port_name', '') or ''
                })
        return edges_list

    def _topo_sort_nodes(self, comp_id: str) -> List[str]:
        """拓扑排序节点列表。"""
        dag = self.get_dag(comp_id)
        nodes_set = set(self.get_nodes(comp_id))

        # 构建邻接表和入度
        degree = {n: 0 for n in nodes_set}
        adj = {n: [] for n in nodes_set}
        for e in dag:
            adj[e["from"]].append(e["to"])
            degree[e["to"]] += 1

        q = [n for n in nodes_set if degree[n] == 0]
        result = []
        while q:
            n = q.pop(0)
            result.append(n)
            for nb in adj[n]:
                degree[nb] -= 1
                if degree[nb] == 0:
                    q.append(nb)
        return result

    def _has_cycle(self, node_set: set, edges_list: List[dict]) -> list:
        """检测 DAG 中是否存在环。返回环中节点列表或空列表（BFS 拓扑排序）。"""
        if not edges_list:
            return []
        adj = {n: [] for n in node_set}
        degree = {n: 0 for n in node_set}
        for e in edges_list:
            if e.get("from") in adj and e.get("to") in adj:
                adj[e["from"]].append(e["to"])
                degree[e["to"]] += 1

        q = [n for n in node_set if degree[n] == 0]
        visited = set()
        while q:
            n = q.pop(0)
            visited.add(n)
            for nb in adj[n]:
                degree[nb] -= 1
                if degree[nb] == 0:
                    q.append(nb)

        remaining = node_set - visited
        return list(remaining) if remaining else []

    # ── 复合节点的对外端口 ──

    def get_external_ports(self, comp_id: str) -> dict:
        """
        返回复合节点对外暴露的端口。

        - 内部节点连线到外部节点 → 复合节点的输出端口
        - 外部节点连线到内部节点 → 复合节点的输入端口
        """
        node_set = set(self.get_nodes(comp_id))
        if not self._canvas:
            return {"inputs": [], "outputs": []}

        inputs, outputs = [], []
        for edge_item in self._canvas.edges:
            src = edge_item.start_node.node_name if hasattr(edge_item.start_node, 'node_name') else ''
            tgt = edge_item.end_node.node_name if hasattr(edge_item.end_node, 'node_name') else ''
            src_in = src in node_set
            tgt_in = tgt in node_set

            if src_in and not tgt_in:
                outputs.append({
                    "name": f"{src}_to_{tgt}",
                    "internal_node": src,
                    "external_node": tgt,
                    "port": getattr(edge_item, 'source_port_name', '') or "output"
                })
            elif not src_in and tgt_in:
                inputs.append({
                    "name": f"{src}_to_{tgt}",
                    "external_node": src,
                    "internal_node": tgt,
                    "port": getattr(edge_item, 'target_port_name', '') or "input"
                })

        return {"inputs": inputs, "outputs": outputs}

    # ── Orchestrator 生成与启动 ──

    def generate_orchestrator(self, comp_id: str) -> str:
        """生成 orchestrator.py 并返回路径。"""
        nodes_list = self.get_nodes(comp_id)
        dag = self.get_dag(comp_id)
        ports = self.get_external_ports(comp_id)

        node_modules = []
        for name in nodes_list:
            node_modules.append({
                "name": name,
                "module": f"nodes.{name}.main",
                "path": f"./nodes/{name}"
            })

        code = render_orchestrator_script(
            comp_id=comp_id,
            node_modules=node_modules,
            dag=dag,
            external_ports=ports
        )
        orch_path = os.path.join(self._project_path, f"orchestrator_{comp_id}.py")
        with open(orch_path, 'w', encoding='utf-8') as f:
            f.write(code)

        self._composites[comp_id]["orchestrator_path"] = orch_path
        self.save()
        return orch_path

    def start_inprocess(self, comp_id: str) -> Tuple[bool, str]:
        """启动 inprocess 模式复合节点。"""
        orch_path = self.generate_orchestrator(comp_id)
        virtual_name = f"__composite_{comp_id}"

        # 检查是否已在运行
        if virtual_name in self._active_processes:
            proc = self._active_processes[virtual_name]
            if proc.poll() is None:
                return False, t(TK.COMPOSITE_ALREADY_RUNNING)

        # 查找 Python 解释器 — 优先使用复合节点独立 venv
        project_root = self._project_path
        comp_dir = self._comp_venv_dir(comp_id)
        python_exe = get_python_exe(comp_dir) or ""

        # 回退: 项目级 venv
        if not python_exe or not os.path.exists(python_exe):
            if os.name == 'nt':
                python_exe = os.path.join(project_root, "venv", "Scripts", "python.exe")
            else:
                python_exe = os.path.join(project_root, "venv", "bin", "python3")
        # 最终回退: 当前 Python
        if not os.path.exists(python_exe):
            python_exe = sys.executable

        proc = None
        try:
            proc = subprocess.Popen(
                [python_exe, orch_path],
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
            )
            self._active_processes[virtual_name] = proc
            logger.info("[%s] 复合节点已启动 PID=%d", comp_id, proc.pid)

            # 启动后健康检查 — 检测进程是否立刻 crash
            import time
            time.sleep(0.3)
            ret = proc.poll()
            if ret is not None:
                stderr_output = ""
                try:
                    stderr_output = proc.stderr.read().decode('utf-8', errors='replace') if proc.stderr else ''
                except Exception:
                    pass
                self._active_processes.pop(virtual_name, None)
                return False, t(TK._COMPOSITE_CRASH).format(code=ret) + f"\n{stderr_output[:500]}"

            # 写入 PID 文件供 BNOS 检测
            pid_file = os.path.join(project_root, f"__composite_{comp_id}.pid")
            with open(pid_file, 'w') as f:
                f.write(str(proc.pid))

            return True, t(TK._COMPOSITE_STARTED).format(pid=proc.pid)
        except Exception as e:
            # S03: 异常时确保 kill 子进程，防止僵尸进程
            if proc is not None and proc.poll() is None:
                try:
                    proc.kill()
                    proc.wait(timeout=5)
                except Exception:
                    pass
            self._active_processes.pop(virtual_name, None)
            logger.error("[%s] 启动失败: %s", comp_id, e)
            return False, str(e)

    def start_process_mode(self, comp_id: str) -> Tuple[bool, str]:
        """启动 process 模式复合节点（各节点独立启动）。"""
        from ui.core.node.node_control_service import node_control_service
        node_names = self.get_nodes(comp_id)
        for n in node_names:
            node_control_service.start_node(n)
        return True, t(TK._COMPOSITE_STARTED_N).format(n=len(node_names))

    def stop_composite(self, comp_id: str) -> Tuple[bool, str]:
        """停止复合节点。"""
        virtual_name = f"__composite_{comp_id}"
        proc = self._active_processes.get(virtual_name)
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            del self._active_processes[virtual_name]
            logger.info("[%s] 复合节点已停止", comp_id)

        # 清理 PID 文件
        pid_file = os.path.join(self._project_path, f"__composite_{comp_id}.pid")
        try:
            os.remove(pid_file)
        except OSError:
            pass

        return True, t(TK.COMPOSITE_STOPPED)

    def is_running(self, comp_id: str) -> bool:
        """检查复合节点是否在运行。"""
        virtual_name = f"__composite_{comp_id}"
        proc = self._active_processes.get(virtual_name)
        return proc is not None and proc.poll() is None

    # ── 辅助 ──

    def _find_composite_of_node(self, node_name: str) -> Optional[str]:
        for cid, c in self._composites.items():
            if node_name in c.get("nodes", []):
                return cid
        return None

    def _find_internal_by_port(self, comp_id: str, port_name: str,
                                port_type: str = "output") -> Optional[str]:
        """Given a composite's port name, return the internal node it maps to.

        Args:
            comp_id: composite node id (e.g. "composite_abc123")
            port_name: anchor port name (e.g. "node_a_in" or "node_b_out")
            port_type: "input" or "output"

        Returns:
            internal node name or None
        """
        comp = self._composites.get(comp_id, {})
        ports_key = "input_ports" if port_type == "input" else "output_ports"
        for port in comp.get(ports_key, []):
            if port.get("port_name") == port_name:
                return port.get("internal_node")
        return None

    def is_node_in_composite(self, node_name: str) -> bool:
        return self._find_composite_of_node(node_name) is not None

    def _detach_from_user_groups(self, node_names: List[str]):
        """将节点从用户手动创建的节点组中移出。"""
        if not self._group_manager:
            return
        for n in node_names:
            current_group = self._group_manager.node_to_group.get(n, "")
            if current_group and not current_group.startswith(GROUP_PREFIX):
                try:
                    self._group_manager.remove_nodes_from_group(current_group, [n])
                except Exception:
                    pass

    def _comp_venv_dir(self, comp_id: str) -> str:
        """获取复合节点的 venv 目录路径。"""
        comp = self._composites.get(comp_id, {})
        display_name = comp.get("display_name", "")
        return comp_venv_path(self._project_path, comp_id, display_name)

    @staticmethod
    def is_composite_group(group_name: str) -> bool:
        """判断一个节点组是否是复合节点自动创建的组。"""
        return group_name.startswith(GROUP_PREFIX)

    def _stop_if_running(self, comp_id: str):
        """停止复合节点的运行。"""
        runtime = self.get_runtime(comp_id)
        if runtime == "inprocess":
            self.stop_composite(comp_id)
        elif runtime == "process":
            from ui.core.node.node_control_service import node_control_service
            for n in self.get_nodes(comp_id):
                try:
                    node_control_service.stop_node(n)
                except Exception:
                    pass

    def _canvas_compress(self, comp_id: str, node_names: list, cx: float, cy: float,
                         display_name: str = "", ports: dict = None):
        """Canvas operation: hide original nodes, show composite node with port anchors."""
        from ui.canvas.items.composite_node_item import CompositeNodeItem

        node_set = set(node_names)

        # Hide original nodes
        for n in node_names:
            item = self._canvas.nodes.get(n)
            if item:
                item.setVisible(False)

        # Hide and store edges between internal nodes (prevent residue)
        # Also hide internal↔external edges (they'll be re-routed through composite ports)
        internal_edge_info = []
        external_edge_info = []
        for edge in list(self._canvas.edges):
            src_name = edge.start_node.node_name if hasattr(edge.start_node, 'node_name') else ''
            tgt_name = edge.end_node.node_name if hasattr(edge.end_node, 'node_name') else ''
            src_in = src_name in node_set
            tgt_in = tgt_name in node_set
            if src_in and tgt_in:
                internal_edge_info.append({
                    "src": src_name, "tgt": tgt_name,
                    "src_port": getattr(edge, 'source_port_name', ''),
                    "tgt_port": getattr(edge, 'target_port_name', ''),
                })
                edge.setVisible(False)
            elif src_in != tgt_in:
                # One endpoint internal, one external
                external_edge_info.append({
                    "src": src_name, "tgt": tgt_name,
                    "src_port": getattr(edge, 'source_port_name', ''),
                    "tgt_port": getattr(edge, 'target_port_name', ''),
                })
                edge.setVisible(False)
        self._composites.setdefault(comp_id, {})["_internal_edges"] = internal_edge_info
        self._composites[comp_id]["_external_edges"] = external_edge_info

        # Create composite node with port info
        input_ports = (ports or {}).get("input_ports", [])
        output_ports = (ports or {}).get("output_ports", [])

        comp_item = CompositeNodeItem(
            comp_id=comp_id,
            node_count=len(node_names),
            node_names=node_names,
            display_name=display_name,
            canvas=self._canvas,
            input_ports=input_ports,
            output_ports=output_ports,
        )
        comp_item.setPos(cx, cy)
        self._canvas.scene.addItem(comp_item)
        self._canvas.nodes[comp_id] = comp_item

    def _canvas_decompress(self, comp_id: str, node_names: list, positions: dict):
        """Canvas: remove composite node, restore original nodes and internal edges."""
        node_set = set(node_names)

        # 移除复合节点
        comp_item = self._canvas.nodes.pop(comp_id, None)
        if comp_item:
            self._canvas.scene.removeItem(comp_item)

        # 还原原始节点位置
        for n in node_names:
            item = self._canvas.nodes.get(n)
            if item:
                pos = positions.get(n, {})
                item.setPos(QPointF(pos.get("x", 0), pos.get("y", 0)))
                item.setVisible(True)

        # Restore internal edges (hidden during compression)
        comp = self._composites.get(comp_id, {})
        for info in comp.get("_internal_edges", []):
            for edge in self._canvas.edges:
                src_name = edge.start_node.node_name if hasattr(edge.start_node, 'node_name') else ''
                tgt_name = edge.end_node.node_name if hasattr(edge.end_node, 'node_name') else ''
                if src_name == info["src"] and tgt_name == info["tgt"]:
                    edge.setVisible(True)
                    break
        # Restore external edges (hidden during compression)
        for info in comp.get("_external_edges", []):
            for edge in self._canvas.edges:
                src_name = edge.start_node.node_name if hasattr(edge.start_node, 'node_name') else ''
                tgt_name = edge.end_node.node_name if hasattr(edge.end_node, 'node_name') else ''
                if src_name == info["src"] and tgt_name == info["tgt"]:
                    edge.setVisible(True)
                    break


# ── Background worker for compress I/O ──

class _CompressWorker(QThread):
    """Runs merge_requirements in a background thread to avoid UI freeze."""

    def __init__(self, project_path: str, comp_id: str, display_name: str,
                 node_names: list, nodes_data: dict, parent=None):
        super().__init__(parent)
        self._project_path = project_path
        self._comp_id = comp_id
        self._display_name = display_name
        self._node_names = node_names
        self._nodes_data = nodes_data
        self._merge_ok = False
        self._merge_msg = ""
        self._compress_data = {}

    def run(self):
        """Run heavy I/O on background thread."""
        self._merge_ok, self._merge_msg = merge_requirements(
            self._project_path,
            self._comp_id,
            self._display_name,
            self._node_names,
            self._nodes_data,
            logger,
        )

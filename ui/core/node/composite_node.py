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

from PySide6.QtCore import QPointF

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
            except Exception as e:
                logger.warning("加载 node_clusters.json 失败: %s", e)
                self._composites = {}

    def save(self):
        data = {"composites": self._composites}
        # 原子写入: tmp → rename
        tmp_path = self._config_path + ".tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self._config_path)

    # ── 核心操作 ──

    def compress(self, node_names: list, name: str = "") -> Tuple[bool, str, Optional[str]]:
        """
        将多个节点压缩为复合节点。

        返回: (成功, 消息, 复合节点ID)

        步骤:
          1. 验证所有节点存在且未属于其他复合节点
          2. 保存原始画布位置
          3. 生成复合节点 ID 和对应节点组名
          4. 在 NodeGroupManager 中创建同名节点组（自动锁定）
          5. 持久化
          6. 隐藏画布原始节点，显示复合节点
        """
        if not self._canvas:
            return False, t(TK.COMPOSITE_CANVAS_UNAVAILABLE), None

        # 1. 验证
        # S07: 最少 2 个节点
        if len(node_names) < 2:
            return False, t(TK.COMPOSITE_NEED_2_NODES), None

        for n in node_names:
            # S06: 禁止嵌套复合
            if n in self._composites:
                return False, t(TK._COMPOSITE_IS_ITSELF).format(name=n), None
            existing = self._find_composite_of_node(n)
            if existing:
                return False, t(TK._COMPOSITE_ALREADY_IN).format(name=n, composite=existing), None
            if n not in self._canvas.nodes:
                return False, t(TK._COMPOSITE_NOT_ON_CANVAS).format(name=n), None

            # S02: 运行中节点禁止压缩
            if self._canvas.parent_window:
                node_data = self._canvas.parent_window.nodes_data.get(n, {})
                status = node_data.get('status', '')
                if status in ('running', 'idle', 'starting', 'stopping'):
                    return False, t(TK._COMPOSITE_RUNNING).format(name=n, status=status), None

        # S11: 语言兼容性检查
        node_langs = {}
        for n in node_names:
            node_data = self._canvas.parent_window.nodes_data.get(n, {}) if self._canvas.parent_window else {}
            node_path = node_data.get('path', '')
            if not node_path:
                node_path = os.path.join(self._project_path, "nodes", n)
            lang = self._canvas.detect_language(node_path) if self._canvas else "Unknown"
            node_langs[n] = lang
        unique_langs = set(node_langs.values())
        if "Unknown" in unique_langs:
            unknown_nodes = [n for n, l in node_langs.items() if l == "Unknown"]
            return False, t(TK.COMPOSITE_UNKNOWN_LANGUAGE).format(nodes=", ".join(unknown_nodes)), None
        if len(unique_langs) > 1:
            lang_summary = {lang: [n for n, l in node_langs.items() if l == lang] for lang in unique_langs}
            msg_parts = [f"{lang}({'、'.join(names)})" for lang, names in lang_summary.items()]
            return False, t(TK.COMPOSITE_LANGUAGE_MISMATCH).format(details=" | ".join(msg_parts)), None

        # S01: DAG 环检测
        # 推导内部 DAG 并检测环
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

        # S10: 孤立节点提示（不阻止，仅 warning）
        if len(node_names) > 1 and edges_list:
            connected = set()
            for e in edges_list:
                connected.add(e["from"])
                connected.add(e["to"])
            isolated = node_set - connected
            if isolated:
                logger.warning("以下节点在压缩集内无连线: %s", isolated)

        # S12: 合并子节点 Python 依赖到复合节点独立 venv
        comp_id = f"composite_{uuid.uuid4().hex[:8]}"
        display_name = name.strip() if name and name.strip() else ""
        nodes_data = self._canvas.parent_window.nodes_data if self._canvas.parent_window else {}
        merge_ok, merge_msg = merge_requirements(
            self._project_path, comp_id, display_name, node_names, nodes_data, logger
        )
        if not merge_ok:
            return False, merge_msg, None

        # 2. 保存原始画布位置
        original_positions = {}
        for n in node_names:
            item = self._canvas.nodes.get(n)
            if item:
                original_positions[n] = {"x": item.pos().x(), "y": item.pos().y()}

        # 3. 组名
        group_name = f"{GROUP_PREFIX}{comp_id}"

        # 4. 在 NodeGroupManager 中创建同名节点组
        if self._group_manager:
            self._detach_from_user_groups(node_names)
            self._group_manager.create_group(group_name, color=GROUP_COLOR)
            self._group_manager.add_nodes_to_group(group_name, node_names)
            self._group_manager.lock_group(group_name)

        # 5. 计算中心位置
        if original_positions:
            cx = sum(p["x"] for p in original_positions.values()) / len(original_positions)
            cy = sum(p["y"] for p in original_positions.values()) / len(original_positions)
        else:
            cx, cy = 0, 0

        # 6. 存储
        self._composites[comp_id] = {
            "nodes": node_names,
            "runtime": "inprocess",
            "group_name": group_name,
            "display_name": display_name,
            "canvas_position": {"x": cx, "y": cy},
            "original_positions": original_positions,
        }
        self.save()

        # 7. 画布操作
        self._canvas_compress(comp_id, node_names, cx, cy, display_name)

        return True, t(TK._COMPOSITE_COMPRESSED).format(n=len(node_names)), comp_id

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

    def _canvas_compress(self, comp_id: str, node_names: list, cx: float, cy: float, display_name: str = ""):
        """画布操作：隐藏原始节点 → 显示复合节点。"""
        from ui.canvas.items.composite_node_item import CompositeNodeItem

        # 隐藏原始节点
        for n in node_names:
            item = self._canvas.nodes.get(n)
            if item:
                item.setVisible(False)

        # 创建复合节点
        comp_item = CompositeNodeItem(
            comp_id=comp_id,
            node_count=len(node_names),
            node_names=node_names,
            display_name=display_name,
            canvas=self._canvas
        )
        comp_item.setPos(cx, cy)
        self._canvas.scene.addItem(comp_item)
        self._canvas.nodes[comp_id] = comp_item

    def _canvas_decompress(self, comp_id: str, node_names: list, positions: dict):
        """画布操作：移除复合节点 → 显示原始节点。"""
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

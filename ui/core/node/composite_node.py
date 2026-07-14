"""
ui/core/composite_node.py
复合节点管理 — 压缩/解耦/运行时切换 / DAG / 持久化。

环境管理 → ui.core.composite_env
编排器生成 → ui.core.composite_orchestrator

与 NodeGroupManager 联动：
  - 压缩 → 自动创建节点组 + 锁定（防止用户手动移出节点）
  - 解耦 → 自动解锁 + 删除节点组
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from PySide6.QtCore import QPointF, QThread

from ui.core.config.config_merger import get_config_path
from ui.core.i18n.i18n import t
from ui.core.i18n.translation_keys import TK
from ui.core.logger import logger
from ui.core.node.composite_env import (
    comp_venv_path,
    get_python_exe,
    merge_requirements,
    remove_comp_env,
)
from ui.core.node.composite_orchestrator import render_orchestrator_script
from ui.core.node.language_detector import LanguageDetector
from ui.core.state.composite_lifecycle import CompositeLifecycleSM
from ui.core.state.node_state_action_service import NodeStateActionService
from ui.core.state.node_state_manager import NodeStateManager
from ui.core.utils.dialog_utils import themed_message

# ── 与 NodeGroupManager 的绑定规则 ──
# 复合节点组命名: __composite__{comp_id}
# 颜色: #4ec9b0（青绿色，匹配复合节点边框）
# 自动锁定: 压缩后 lock_group，防止用户手动移出节点
# 解耦时: unlock_group → delete_group
# 用户手动创建的节点组（无 __composite__ 前缀）不受影响

GROUP_PREFIX = "__composite__"
GROUP_COLOR = "#4ec9b0"
COMPOSITE_NODES_DIR = "composite_nodes"  # 复合节点专属目录
ARCHIVE_DIR = ".archive"  # 日志存档子目录
ARCHIVE_MAX_COUNT = 10  # 最大存档数

# Phase4.1 RouteCache._guess_composite_json_path 用：记录最近一次初始化的 project_path
# （多窗口/多项目场景会被覆盖，但 flush 发生时几乎一定是「当前活跃项目」路径，故能命中）
_LAST_SEEN_PROJECT_PATH: str | None = None

# ── Phase4.1 灰度开关：expand/collapse morph「先删后建 + 配置互斥交接」新机制
#    True  → 使用新的 6 步三阶段分离 morph（推荐，修 Bug D/F/G）
#    False → 退回旧的「anchor morph 平移 + 保留原边对象」代码（仅开发期兜底，
#            灰度 1 周零误报后删除旧分支与本开关）
USE_MORPH_MUTEX_SWITCH: bool = True


# ── Morph 路由条目数据结构（供 collect_*_morph_list 返回使用）──
# 每个 dict 字段含义：
#   direction:          "input"  (external → comp / external → child)
#                       "output" (comp → external / child → external)
#   ===== input direction =====
#   in_port:            comp 的输入端口名（折叠态时）
#   upstream_node_id:   上游外部节点名（e.g. "node_python_a"）
#   upstream_out_port:  上游输出端口（通常 "default"）
#   source_output_path: 上游 output.json 绝对路径（= 要写进 child listen_upper_file 的值）
#   target_child_name:  复合内部接收端子节点名
#   target_child_port:  子节点接收端口（"default" 或其他 port_mappings 名）
#   ===== output direction =====
#   out_port:           comp 的输出端口名（折叠态时）
#   child_source_name:  复合内部作为发送端的子节点名
#   child_source_port:  子节点发送端口（通常 "default"）
#   downstream_node_id: 下游外部节点名
#   downstream_in_port: 下游接收端口（"default" 或其他）


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
        global _LAST_SEEN_PROJECT_PATH
        self._project_path = project_path
        _LAST_SEEN_PROJECT_PATH = project_path
        self._canvas = canvas
        self._group_manager = group_manager
        self._composites: dict[str, dict] = {}
        self._config_path = Path(project_path) / "node_clusters.json"
        self._active_processes: dict[str, subprocess.Popen] = {}
        self._composite_log_files: dict[str, tuple] = {}
        self._lifecycle: dict[str, CompositeLifecycleSM] = {}
        # ── 节点统一状态机（阶段三灰度接入：并行双写，差异告警，不替换旧逻辑）
        #    单例：canvas._node_state_manager 与 self._node_state_manager 指向同一实例
        #    canvas_connections 可通过 canvas._node_state_manager 拿到 handle_event 入口
        self._node_state_manager: NodeStateManager | None = None
        self._node_state_action_svc: NodeStateActionService | None = None
        self._init_state_manager_singleton()
        # ──
        self.load()

    def _init_state_manager_singleton(self) -> None:
        """构建 NodeStateManager + NodeStateActionService 单例。

        单例优先级：
          1. 若 self._canvas 已经挂了 _node_state_manager（NodeCanvas.__init__ 提前挂好的）
             → 直接复用该实例，只补注入 composite_manager_ref 即可（避免两套单例各跑各的）
          2. 否则 → 新建一套，挂到 canvas 和 self 上

        - self._node_state_manager: CompositeNode 持有引用（供 expand/collapse/compress/decompress 调用）
        - self._canvas._node_state_manager: 画布引用（供 canvas_connections.create_edge/remove_edge 调用）
        - 所有异常静默吞掉：灰度接入阶段不希望因为状态机初始化失败导致旧功能崩溃
        """
        try:
            existing_svc = None
            existing_mgr = getattr(self._canvas, "_node_state_manager", None) if self._canvas is not None else None
            if existing_mgr is not None:
                # 路径 1：canvas 已经有共享单例（NodeCanvas.__init__ 提前创建）→ 直接复用
                self._node_state_manager = existing_mgr
                try:
                    existing_mgr._composite_mgr = self  # 补注入 composite_manager_ref
                except Exception:  # noqa: BLE001
                    pass
                existing_svc = getattr(existing_mgr, "_action_svc", None)
                if existing_svc is not None:
                    self._node_state_action_svc = existing_svc
                    try:
                        existing_svc._composite_mgr = self  # 补注入
                    except Exception:  # noqa: BLE001
                        pass
                    logger.info("[Phase3-gray-INIT] NodeStateManager singleton reused from canvas (OK)")
                    return
                # 老单例没有 action_svc → 给他配一个
                svc = NodeStateActionService(existing_mgr, composite_manager_ref=self)
                existing_mgr._action_svc = svc
                self._node_state_action_svc = svc
                logger.info(
                    "[Phase3-gray-INIT] NodeStateManager singleton reused from canvas, ActionService attached (OK)"
                )
                return

            # 路径 2：canvas 没有共享单例 → 新建
            mgr = NodeStateManager(composite_manager_ref=self)
            svc = NodeStateActionService(mgr, composite_manager_ref=self)
            mgr._action_svc = svc
            self._node_state_manager = mgr
            self._node_state_action_svc = svc
            if self._canvas is not None:
                self._canvas._node_state_manager = mgr
            logger.info("[Phase3-gray-INIT] NodeStateManager singleton initialized via CompositeNodeManager (OK)")
        except Exception as e:  # noqa: BLE001 - 灰度阶段：任何异常均不影响旧代码启动
            logger.warning(
                "[Phase3-gray-INIT-FAIL] NodeStateManager singleton init via CompositeNodeManager failed (non-fatal): %s",
                e,
            )
            self._node_state_manager = None
            self._node_state_action_svc = None

    # ─────────── Phase3 灰度接入：复合节点批量事件并行双写（不替换旧逻辑，仅告警差异）───────────

    def _gray_register_comp(self, comp_id: str) -> None:
        """幂等注册复合节点本体 + 所有子节点。"""
        mgr = self._node_state_manager
        if mgr is None:
            return
        comp = self._composites.get(comp_id, {})
        children = list(comp.get("nodes") or [])
        entry = comp.get("entry_node") or (children[0] if children else "")
        if not mgr.is_registered(comp_id):
            try:
                mgr.register_composite(
                    comp_id=comp_id,
                    child_names=children,
                    entry_node=entry,
                    initially_collapsed=not comp.get("_expanded", False),
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("[Phase3-gray] register_composite %s failed: %s", comp_id, e)
        for c in children:
            if mgr.is_registered(c):
                continue
            try:
                mgr.register_composite_child(
                    c,
                    comp_id=comp_id,
                    initially_hidden=not comp.get("_expanded", False),
                )
            except Exception as e:  # noqa: BLE001
                logger.warning("[Phase3-gray] register_composite_child %s failed: %s", c, e)

    def _gray_diff(self, who: str, action: str, ok: bool, detail: str = ""):
        """统一的差异告警输出 + 成功日志（不影响主流程返回值）。"""
        if ok:
            logger.info(
                "[Phase3-gray-%s OK] %s%s",
                action,
                who,
                (f" ({detail})" if detail else ""),
            )
            return
        logger.warning(
            "[Phase3-gray-DIFF] %s state-machine %s rejected. Old logic still applied. %s",
            who,
            action,
            detail,
        )

    def _gray_expand(self, comp_id: str) -> None:
        """_expand_composite 成功后：并行调用 comp.handle_event('expand')。"""
        try:
            mgr = self._node_state_manager
            if mgr is None:
                return
            self._gray_register_comp(comp_id)
            ok = mgr.handle_event(comp_id, "expand")
            self._gray_diff(comp_id, "expand", ok)
        except Exception as e:  # noqa: BLE001
            logger.warning("[Phase3-gray] expand handle_event skip (non-fatal): %s", e)

    def _gray_collapse(self, comp_id: str) -> None:
        """_collapse_composite 成功后：并行调用 comp.handle_event('collapse')。"""
        try:
            mgr = self._node_state_manager
            if mgr is None:
                return
            self._gray_register_comp(comp_id)
            ok = mgr.handle_event(comp_id, "collapse")
            self._gray_diff(comp_id, "collapse", ok)
        except Exception as e:  # noqa: BLE001
            logger.warning("[Phase3-gray] collapse handle_event skip (non-fatal): %s", e)

    def _gray_compress(self, comp_id: str) -> None:
        """compress 成功后：并行调用所有子节点 compress_into_composite。"""
        try:
            mgr = self._node_state_manager
            if mgr is None:
                return
            self._gray_register_comp(comp_id)
            comp = self._composites.get(comp_id, {})
            children = list(comp.get("nodes") or [])
            for child in children:
                if not mgr.is_registered(child):
                    try:
                        mgr.register_standalone(child)  # 确保有注册才触发 compress_into_composite
                    except Exception:  # noqa: BLE001
                        pass
                ok = mgr.handle_event(child, "compress_into_composite")
                self._gray_diff(child, "compress_into_composite", ok, f"parent={comp_id}")
        except Exception as e:  # noqa: BLE001
            logger.warning("[Phase3-gray] compress batch skip (non-fatal): %s", e)

    def _gray_decompress(self, comp_id: str, children: list[str]) -> None:
        """decompress 成功后：并行调用每个子节点 decompress_from_composite。"""
        try:
            mgr = self._node_state_manager
            if mgr is None:
                return
            for child in children:
                if not mgr.is_registered(child):
                    try:
                        mgr.register_composite_child(child, comp_id=comp_id, initially_hidden=False)
                    except Exception:  # noqa: BLE001
                        try:
                            mgr.register_standalone(child)
                        except Exception:  # noqa: BLE001
                            pass
                ok = mgr.handle_event(child, "decompress_from_composite")
                self._gray_diff(child, "decompress_from_composite", ok, f"parent={comp_id}")
        except Exception as e:  # noqa: BLE001
            logger.warning("[Phase3-gray] decompress batch skip (non-fatal): %s", e)

    # ──────────────────────────────────────────────────────────────────────────────────

    def load(self):
        if self._config_path.exists():
            try:
                with self._config_path.open(encoding="utf-8") as f:
                    self._composites = json.load(f).get("composites", {})
                # Auto-collapse any expanded composites from previous session
                for _comp_id, comp in list(self._composites.items()):
                    if comp.get("_expanded"):
                        comp["_expanded"] = False
                        if "_drag_anchor_positions" in comp:
                            del comp["_drag_anchor_positions"]
            except Exception as e:
                logger.warning("加载 node_clusters.json 失败: %s", e)
                self._composites = {}
        # 迁移已有复合节点（缺失 composite.json 的自动创建）
        self._migrate_existing_composites()

    def save(self):
        """Atomic write to node_clusters.json (immediate, not debounced).
        Uses retry logic to handle transient file locks (antivirus, indexing)."""
        if getattr(self, "_saving", False):
            return  # Concurrent save already in progress

        import time

        self._saving = True
        try:
            # Strip non-serializable runtime fields (_morphed_edges contains EdgeItem Qt objects)
            cleaned = {}
            for comp_id, comp in self._composites.items():
                cleaned[comp_id] = {k: v for k, v in comp.items() if k != "_morphed_edges"}
            data = {"composites": cleaned}
            tmp_path = Path(str(self._config_path) + ".tmp")

            # Write to temp file
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # Atomic replace with retry for Windows file lock issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    tmp_path.replace(self._config_path)
                    break
                except PermissionError:
                    if attempt < max_retries - 1:
                        time.sleep(0.1 * (attempt + 1))
                    else:
                        # Last resort: delete target then rename
                        try:
                            self._config_path.unlink()
                            tmp_path.replace(self._config_path)
                        except Exception:
                            logger.error("save: cannot write %s after %d retries", self._config_path, max_retries)
                except OSError as e:
                    logger.error("save: OS error on %s: %s", self._config_path, e)
                    break
        finally:
            self._saving = False

    # ── 复合节点端口路由（_port_routing）──
    # 路由信息存储在 node_clusters.json 的每个 composite 的 _port_routing 字段中，
    # 而非内部节点的 node_config.json。这样 listen_upper_file 保持为空，端口识别不受影响。
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

    def set_input_routing(
        self,
        comp_id: str,
        port_name: str,
        source_output_path: str,
        *,
        target_node: str | None = None,
        target_port: str | None = None,
        upstream_node_id: str | None = None,
        upstream_out_port: str | None = None,
    ):
        """记录输入端口的路由：上游 output.json → 本复合节点的入口。

        project_memory 硬约束：Composite node input anchor names must map data (internal) to
        default (external) for correct port identification.
        → 任何调用方（create_edge / collapse sync / morph）传入 default 或 data 都统一规范化成
          内部标准名 "data"，避免 composite.json.external_connections.input 中同时出现
          default 和 data 两个重复条目 → morph_list 翻倍 → MUTEX-VIOLATION expand 断言。
        """
        comp = self._composites.get(comp_id)
        if not comp:
            return
        raw_port = (port_name or "").strip() or "default"
        if raw_port in {"data", "default"}:
            # 主入口别名：内部统一存 "data"（内部路由名）
            norm_port = "data"
        else:
            norm_port = raw_port
        self._ensure_port_routing(comp_id)
        entry: dict = {"source_output_path": source_output_path}
        if target_node:
            entry["target_node"] = target_node
        if target_port:
            entry["target_port"] = target_port
        if upstream_node_id:
            entry["_upstream_node_id"] = upstream_node_id
        if upstream_out_port:
            entry["_upstream_out_port"] = upstream_out_port
        comp["_port_routing"]["input"][norm_port] = entry
        # 如果用户传入别名且和 norm 不同，同时清掉旧别名（避免历史数据残留）
        if raw_port != norm_port and raw_port in comp["_port_routing"]["input"]:
            del comp["_port_routing"]["input"][raw_port]
        self.save_debounced()
        self._sync_routing_debounced(comp_id)
        self._sync_routing_to_config(comp_id)
        logger.info(
            "[COMPOSITE-ROUTE-SYNC] set_input comp=%s raw_port=%s norm_port=%s src=%s tgt=%s|%s upstream=%s:%s",
            comp_id,
            raw_port,
            norm_port,
            source_output_path,
            target_node or "",
            target_port or "",
            upstream_node_id or "",
            upstream_out_port or "",
        )

    def set_output_routing(
        self, comp_id: str, port_name: str, target_composite: str | None, target_node: str, target_port: str
    ):
        """记录输出端口的路由：本复合节点的输出 → 下游节点。

        project_memory 硬约束：Output anchor names map node_output (internal) to default (external).
        → 任何调用方传入 default 或 node_output 都统一规范化成内部标准名 "node_output"。
        """
        comp = self._composites.get(comp_id)
        if not comp:
            return
        raw_port = (port_name or "").strip() or "default"
        if raw_port in {"default", "node_output"}:
            norm_port = "node_output"
        else:
            norm_port = raw_port
        self._ensure_port_routing(comp_id)
        comp["_port_routing"]["output"][norm_port] = {
            "target_composite": target_composite,
            "target_node": target_node,
            "target_port": target_port,
        }
        if raw_port != norm_port and raw_port in comp["_port_routing"]["output"]:
            del comp["_port_routing"]["output"][raw_port]
        self.save_debounced()
        self._sync_routing_debounced(comp_id)
        self._sync_routing_to_config(comp_id)
        logger.info(
            "[COMPOSITE-ROUTE-SYNC] set_output comp=%s raw_port=%s norm_port=%s tgt=%s|%s",
            comp_id,
            raw_port,
            norm_port,
            target_node,
            target_port,
        )

    def clear_input_routing(self, comp_id: str, port_name: str, *, immediate: bool = False):
        """清除输入端口路由记录。

        immediate=True: 立即写入 composite.json（不走 debounce），
        对应 project_memory 约束：外部→复合节点删除连线后必须立即写盘，
        防止 expand 从磁盘 merge 读回残留。

        支持端口别名宽松匹配：data↔default 任一口径传入都能命中（兼容历史遗留脏数据）。
        """
        comp = self._composites.get(comp_id, {})
        routing = comp.get("_port_routing", {}).get("input", {})
        raw_port = (port_name or "").strip() or "default"
        candidate_ports: list[str] = [raw_port]
        if raw_port in {"data", "default"}:
            candidate_ports = ["data", "default"]
        deleted_any = False
        for p in candidate_ports:
            if p in routing:
                del routing[p]
                deleted_any = True
        if deleted_any:
            self.save_debounced()
            if immediate:
                self._sync_routing_to_config(comp_id)
            else:
                self._sync_routing_debounced(comp_id)
                self._sync_routing_to_config(comp_id)
            logger.info(
                "[COMPOSITE-ROUTE-SYNC] clear_input comp=%s raw_port=%s deleted=%s immediate=%s",
                comp_id,
                raw_port,
                [p for p in candidate_ports if p not in routing],
                immediate,
            )

    def clear_input_routing_all_matching(
        self,
        comp_id: str,
        *,
        source_output_path: str | None = None,
        upstream_node_id: str | None = None,
        upstream_out_port: str | None = None,
        immediate: bool = False,
    ) -> int:
        """清除 routing.input 中所有匹配上游的端口条目（跨 default/data/... 多键同时清）。

        匹配规则：
          - source_output_path 指定：完全相等即命中（字符串规范化比较）
          - upstream_node_id 指定：条目 _upstream_node_id 相等或 source_output_path 中包含该目录名即命中
        返回被删除的端口个数。
        """
        comp = self._composites.get(comp_id, {})
        routing = comp.setdefault("_port_routing", {}).setdefault("input", {})
        if not isinstance(routing, dict):
            return 0

        def _norm(p: str | None) -> str:
            if not p:
                return ""
            try:
                return str(Path(p).resolve()).lower().replace("\\", "/")
            except Exception:
                return str(p).lower().replace("\\", "/")

        to_del: list[str] = []
        norm_target = _norm(source_output_path)
        for port_name, entry in list(routing.items()):
            if not isinstance(entry, dict):
                continue
            hit = False
            if norm_target and _norm(entry.get("source_output_path")) == norm_target:
                hit = True
            if not hit and upstream_node_id:
                up = entry.get("_upstream_node_id")
                if up == upstream_node_id:
                    hit = True
                elif (
                    upstream_out_port
                    and entry.get("_upstream_out_port") == upstream_out_port
                    and up == upstream_node_id
                ):
                    hit = True
                # loose match：source_output_path 里包含 upstream 对应的目录名
                if not hit:
                    src_p = _norm(entry.get("source_output_path"))
                    if upstream_node_id.startswith("node_"):
                        tail = upstream_node_id[len("node_") :]
                        loose_segments = (tail, upstream_node_id)
                    else:
                        loose_segments = (upstream_node_id,)
                    for seg in loose_segments:
                        if seg and seg.lower().replace("\\", "/") in src_p:
                            hit = True
                            break
            if hit:
                to_del.append(port_name)

        for p in to_del:
            del routing[p]
        if to_del:
            self.save_debounced()
            if immediate:
                self._sync_routing_to_config(comp_id)
            else:
                self._sync_routing_debounced(comp_id)
                self._sync_routing_to_config(comp_id)
            logger.info(
                "[COMPOSITE-ROUTE-SYNC] clear_input_all_matching comp=%s deleted_ports=%s upstream=%s:%s src=%s immediate=%s",
                comp_id,
                to_del,
                upstream_node_id or "",
                upstream_out_port or "",
                source_output_path or "",
                immediate,
            )
        return len(to_del)

    def clear_output_routing(self, comp_id: str, port_name: str, *, immediate: bool = False):
        """清除输出端口路由记录。支持端口别名宽松匹配：default↔node_output 任一口径传入都能命中。"""
        comp = self._composites.get(comp_id, {})
        routing = comp.get("_port_routing", {}).get("output", {})
        raw_port = (port_name or "").strip() or "default"
        candidate_ports: list[str] = [raw_port]
        if raw_port in {"default", "node_output"}:
            candidate_ports = ["node_output", "default"]
        deleted_any = False
        for p in candidate_ports:
            if p in routing:
                del routing[p]
                deleted_any = True
        if deleted_any:
            self.save_debounced()
            if immediate:
                self._sync_routing_to_config(comp_id)
            else:
                self._sync_routing_debounced(comp_id)
                self._sync_routing_to_config(comp_id)
            logger.info(
                "[COMPOSITE-ROUTE-SYNC] clear_output comp=%s raw_port=%s deleted=%s immediate=%s",
                comp_id,
                raw_port,
                [p for p in candidate_ports if p not in routing],
                immediate,
            )

    def clear_output_routing_all_matching(
        self,
        comp_id: str,
        *,
        downstream_node_id: str | None = None,
        downstream_in_port: str | None = None,
        immediate: bool = False,
    ) -> int:
        """清除 routing.output 中所有匹配下游的端口条目（跨多键同时清）。返回删除端口数。"""
        comp = self._composites.get(comp_id, {})
        routing = comp.setdefault("_port_routing", {}).setdefault("output", {})
        if not isinstance(routing, dict):
            return 0
        to_del: list[str] = []
        for port_name, entry in list(routing.items()):
            if not isinstance(entry, dict):
                continue
            hit = False
            if downstream_node_id and entry.get("target_node") == downstream_node_id:
                hit = True
            if (
                downstream_in_port
                and entry.get("target_port") == downstream_in_port
                and entry.get("target_node") == downstream_node_id
            ):
                hit = True
            if hit:
                to_del.append(port_name)
        for p in to_del:
            del routing[p]
        if to_del:
            self.save_debounced()
            if immediate:
                self._sync_routing_to_config(comp_id)
            else:
                self._sync_routing_debounced(comp_id)
                self._sync_routing_to_config(comp_id)
            logger.info(
                "[COMPOSITE-ROUTE-SYNC] clear_output_all_matching comp=%s deleted_ports=%s downstream=%s:%s immediate=%s",
                comp_id,
                to_del,
                downstream_node_id or "",
                downstream_in_port or "",
                immediate,
            )
        return len(to_del)

    def _sync_routing_debounced(self, comp_id: str):
        """延迟同步 _port_routing 到 composite.json，避免频繁写入。"""
        from PySide6.QtCore import QTimer

        if not hasattr(self, "_routing_sync_timers"):
            self._routing_sync_timers: dict[str, QTimer] = {}
        if comp_id in self._routing_sync_timers:
            self._routing_sync_timers[comp_id].stop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(lambda cid=comp_id: self._sync_routing_to_config(cid))
        self._routing_sync_timers[comp_id] = timer
        timer.start(300)

    def _sync_routing_to_config(self, comp_id: str):
        """将当前 _port_routing 同步写入 composite.json。"""
        cfg = self._load_composite_config(comp_id)
        if not cfg:
            return
        routing = self._get_port_routing(comp_id)
        if cfg.get("external_connections") == routing:
            return
        cfg["external_connections"] = routing
        self._write_composite_config(comp_id, cfg)
        # 写后立即回读验证 + 详细日志，确保 source_output_path / target 等真的落到磁盘
        written = self._load_composite_config(comp_id)
        ext = written.get("external_connections", {}) if written else {}
        in_keys = sorted((ext.get("input") or {}).keys())
        out_keys = sorted((ext.get("output") or {}).keys())
        in_details = {}
        for k in in_keys:
            v = (ext.get("input") or {}).get(k) or {}
            in_details[k] = {
                "source_output_path": v.get("source_output_path"),
                "source_node": v.get("source_node"),
                "source_port": v.get("source_port"),
            }
        logger.info(
            "[COMPOSITE-ROUTE-SYNC] written-to-disk comp=%s input_ports=%s output_ports=%s input_details=%s",
            comp_id,
            in_keys,
            out_keys,
            in_details,
        )

    # ── 持久化（续）──

    def save_debounced(self):
        """Debounced version: delays write until no further calls for 500ms.
        Used by itemChange during drag to avoid disk I/O spam (60fps)."""
        from PySide6.QtCore import QTimer

        if not hasattr(self, "_save_timer"):
            self._save_timer = QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self.save)
        self._save_timer.stop()
        self._save_timer.start(500)

    # ── Port Identification ──

    def _identify_ports(self, node_names: list, edges_list: list, nodes_data: dict) -> dict:
        """Identify input and output ports for a composite node.

        Input ports: main port + sub-ports derived from the entry node's
            ``input_ports`` config (only ports with source="node").
            The entry node is the DAG node with in-degree 0 and empty
            listen_upper_file.

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

        # ── Input ports: main + sub-ports from entry node's input_ports config ──
        input_ports = []
        node_set_lookup = node_set  # alias for readability
        for n in node_names:
            if in_degree[n] == 0:
                nd = nodes_data.get(n, {})
                config = nd.get("config", {})
                listen = config.get("listen_upper_file", "")
                # 判断该节点是否为真正的入口：
                # 1. listen 为空 → 肯定入口
                # 2. listen 指向复合节点内部的节点 → listen 是展开前的陈旧值，仍视为入口
                is_entry = not listen
                if not is_entry and listen:
                    upstream = self._extract_node_from_path(listen)
                    if upstream and upstream in node_set_lookup:
                        is_entry = True  # stale listen from previous DAG topology

                if is_entry:
                    entry_node = n
                    # Main input port (always present)
                    input_ports.append(
                        {
                            "internal_node": n,
                            "type": "input",
                            "port_name": "data",
                            "display_name": "数据输入",
                            "entry_port": None,
                        }
                    )

                    # Sub-ports from entry node's input_ports config
                    # Priority: use nodes_data (already loaded with correct path mapping)
                    nd_entry = nodes_data.get(entry_node, {})
                    entry_config = nd_entry.get("config", {}) or self._read_node_config(entry_node)
                    entry_input_ports = entry_config.get("input_ports", [])
                    if isinstance(entry_input_ports, list):
                        for port in entry_input_ports:
                            if not isinstance(port, dict):
                                continue
                            if port.get("source") == "node":
                                port_name = port.get("name", "")
                                if not port_name:
                                    continue
                                input_ports.append(
                                    {
                                        "internal_node": n,
                                        "type": "input",
                                        "port_name": port_name,
                                        "display_name": port.get("label", port_name),
                                        "entry_port": port_name,
                                    }
                                )
                    break  # Single-entry DAG — found and processed

        # Output ports: all DAG leaf nodes (out_degree 0)
        output_ports = []
        port_nodes_seen = set()
        for n in node_names:
            if out_degree[n] == 0:
                output_ports.append(
                    {
                        "internal_node": n,
                        "type": "output",
                        "port_name": f"{n}_out",
                        "display_name": n,
                    }
                )
                port_nodes_seen.add(n)

        # Non-terminal nodes with external out_connections → fan-out ports
        # 展开态下内部非叶子节点连了外部节点 → 折叠后为其创建输出端口
        for n in node_names:
            if n in port_nodes_seen:
                continue
            nd = nodes_data.get(n, {})
            cfg = nd.get("config", {})
            out_conns = cfg.get("out_connections", {})
            if not isinstance(out_conns, dict):
                continue
            has_external = False
            for target in out_conns.values():
                if isinstance(target, str) and target:
                    ext_node = target.split("|")[0]
                    if ext_node and ext_node not in node_set:
                        has_external = True
                        break
            if has_external:
                output_ports.append(
                    {
                        "internal_node": n,
                        "type": "output",
                        "port_name": f"{n}_out",
                        "display_name": n,
                    }
                )
                port_nodes_seen.add(n)

        return {
            "input_ports": input_ports,
            "output_ports": output_ports,
        }

    def _read_node_config(self, node_name: str) -> dict:
        """Read the node's unified/legacy config, returning a dict."""
        config_dir = self._find_node_config_dir(node_name)
        if not config_dir:
            return {}

        config_path = Path(get_config_path(str(config_dir)))
        if not config_path or not config_path.exists():
            return {}

        try:
            return json.loads(config_path.read_text(encoding="utf-8")) or {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _find_node_config_dir(self, node_name: str):
        """Locate a node directory by name under nodes/ or composite_nodes/."""
        for base in ["nodes", "composite_nodes"]:
            candidate = Path(self._project_path) / base / node_name
            if candidate.is_dir():
                return candidate
        return None

    def _extract_entry_filter_rules(self, node_names: list, edges_list: list, nodes_data: dict) -> dict | None:
        """提取入口节点的过滤规则（filter + input_ports）。

        用于复合节点轮询时做数据类型匹配，规则等同入口节点的 node_config.json。

        Returns:
            dict with entry_node / filter / input_ports, or None if no entry found.
        """
        node_set = set(node_names)
        in_degree = {n: 0 for n in node_names}
        for e in edges_list:
            if e.get("from") in node_set and e.get("to") in node_set:
                in_degree[e["to"]] += 1

        for n in node_names:
            if in_degree[n] == 0:
                nd = nodes_data.get(n, {})
                config = nd.get("config", {})
                listen = config.get("listen_upper_file", "")
                if not listen:
                    # Priority: use nodes_data (already loaded with correct path mapping)
                    entry_config = config or self._read_node_config(n)
                    return {
                        "entry_node": n,
                        "filter": entry_config.get("filter", {}),
                        "input_ports": entry_config.get("input_ports", []),
                    }
        return None

    def _validate_dag_single_entry(self, node_names: list, edges_list: list, nodes_data: dict) -> tuple[bool, str]:
        """Validate DAG has exactly one entry node (in_degree==0).

        防错机制：复合节点必须为单入口 DAG（A→B→C 或 A→B 同时 A→C）。
        多入口 DAG（如 A→C 且 B→C）不允许创建或折叠。

        仅检查 DAG 入度结构，不检查 listen_upper_file。
        listen_upper_file 在展开态由 _port_routing 注入，不代表 DAG 结构，
        且折叠时 _sync_configs_for_collapse 会将其清除。

        Returns:
            (is_valid, error_message)
        """
        in_degree = {n: 0 for n in node_names}
        for e in edges_list:
            if e.get("from") in node_names and e.get("to") in node_names:
                in_degree[e["to"]] += 1

        candidates = [n for n in node_names if in_degree[n] == 0]

        if len(candidates) == 0:
            return False, t(TK._COMPOSITE_NO_ENTRY)
        if len(candidates) > 1:
            return False, t(TK._COMPOSITE_MULTI_ENTRY).format(count=len(candidates), nodes=", ".join(candidates))
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

        # ⚠️ expand 中途如果抛异常（如 mutex assertion），UI 已经更新（子节点可见，
        # comp_item.is_expanded=True），但 comp["_expanded"] 还没设 → 两个标志分叉。
        # 此时若用 comp["_expanded"] 判断会走反分支（折叠态仍 expand）→ 第一遍无反应。
        # 解决方案：两者不一致时，以 comp_item.is_expanded（用户看到的 UI 状态）为准。
        manager_expanded = bool(comp.get("_expanded", False))
        ui_expanded = bool(getattr(comp_item, "is_expanded", False))
        # 若 frame 存在（展开态才有）也作为辅助判断依据
        frame_exists = f"__frame__{comp_id}" in self._canvas.nodes
        effective_expanded = ui_expanded or (frame_exists and not comp_item.isVisible())

        if manager_expanded != effective_expanded:
            logger.warning(
                "[TOGGLE-DESYNC] comp=%s manager._expanded=%s comp_item.is_expanded=%s "
                "frame_exists=%s comp_item.visible=%s → 以 UI 实际状态 effective_expanded=%s 为准",
                comp_id,
                manager_expanded,
                ui_expanded,
                frame_exists,
                comp_item.isVisible(),
                effective_expanded,
            )

        if effective_expanded:
            self._collapse_composite(comp_id, comp_item)
        else:
            self._expand_composite(comp_id, comp_item)

    def _expand_composite(self, comp_id: str, comp_item):
        """Expand composite: 三阶段严格分离（先收集→再删→后建）。

        USE_MORPH_MUTEX_SWITCH=False → 回退旧的 anchor-morph 平移（开发期兜底）。
        """
        comp = self._composites.get(comp_id) or {}
        logger.info(
            "[MORPH-EXPAND-SUMMARY] ==== EXPAND START comp=%s USE_MORPH_MUTEX_SWITCH=%s "
            "manager._expanded=%s comp_item.is_expanded=%s scene_exists=%s",
            comp_id,
            USE_MORPH_MUTEX_SWITCH,
            comp.get("_expanded", False),
            getattr(comp_item, "is_expanded", None),
            comp_item.scene() is not None,
        )
        if not comp:
            logger.info("[MORPH-EXPAND-SUMMARY] comp=%s ABORT: comp not in _composites", comp_id)
            return
        if comp.get("_expanded"):
            logger.info("[MORPH-EXPAND-SUMMARY] comp=%s ABORT: already expanded", comp_id)
            return
        if comp_item.scene() is None:
            logger.info("[MORPH-EXPAND-SUMMARY] comp=%s ABORT: comp_item.scene() is None", comp_id)
            return

        node_names = list(comp.get("nodes", []) or [])
        if not node_names:
            logger.info("[MORPH-EXPAND-SUMMARY] comp=%s ABORT: internal nodes empty", comp_id)
            return

        # Guard: check all internal node items still exist on canvas
        missing_nodes = []
        for n in list(node_names):
            if n not in self._canvas.nodes:
                missing_nodes.append(n)
                logger.warning("_expand_composite: internal node %s missing from canvas, removing from composite", n)
        for n in missing_nodes:
            node_names.remove(n)
            if "original_positions" in comp and n in comp["original_positions"]:
                del comp["original_positions"][n]
        if not node_names:
            logger.warning("_expand_composite: no internal nodes remaining for %s", comp_id)
            return

        positions = comp.get("original_positions", {})
        comp_pos = {"x": comp_item.pos().x(), "y": comp_item.pos().y()}
        comp["canvas_position"] = comp_pos

        # ── 灰度开关回退：旧 anchor-morph 平移实现 ──
        if not USE_MORPH_MUTEX_SWITCH:
            logger.info("[MORPH-EXPAND-SUMMARY] comp=%s ROUTE: OLD fallback anchor-morph", comp_id)
            comp_item.setVisible(False)
            comp_item.is_expanded = True
            self._canvas._batch_updating = True
            try:
                child_items = []
                for n in node_names:
                    item = self._canvas.nodes.get(n)
                    if item:
                        pos = positions.get(n, {"x": 0, "y": 0})
                        item.setPos(comp_pos.get("x", 0) + pos.get("x", 0), comp_pos.get("y", 0) + pos.get("y", 0))
                        item.setVisible(True)
                        child_items.append(item)
            finally:
                self._canvas._batch_updating = False
            self._morph_composite_to_internal_edges(comp_id, comp_item, node_names)
            self._batch_update_edges_for_nodes(node_names)
            for info in comp.get("_internal_edges", []):
                for edge in self._canvas.edges:
                    src_name = edge.start_node.node_name if hasattr(edge.start_node, "node_name") else ""
                    tgt_name = edge.end_node.node_name if hasattr(edge.end_node, "node_name") else ""
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
            comp["_expanded"] = True
            comp["_child_items"] = node_names
            self.save()
            self._gray_expand(comp_id)
            return

        logger.info(
            "[MORPH-EXPAND-SUMMARY] comp=%s ROUTE: NEW 3-phase morph mutex (internal nodes=%d)",
            comp_id,
            len(node_names),
        )

        # ═══════════════════════════════════════════════════════════════════
        # Phase4.1 新机制：6 步三阶段严格分离（修 Bug D/F/G）
        # ═══════════════════════════════════════════════════════════════════

        # ── 步骤 1 [阶段A 只读收集]：在 comp 配置/UI 边/EdgeKey 全部完好未动时抄真相 ──
        morph_list = self.collect_expand_morph_list(comp_id)
        input_cnt = sum(1 for it in morph_list if it.get("direction") == "input")
        output_cnt = sum(1 for it in morph_list if it.get("direction") == "output")
        logger.info(
            "[MORPH-EXPAND-SUMMARY] comp=%s PhaseA-COLLECT total=%d (input=%d output=%d)\n  morph_list_keys=%s",
            comp_id,
            len(morph_list),
            input_cnt,
            output_cnt,
            [{k: v for k, v in it.items() if k != "_stale"} for it in morph_list],
        )

        # ── 步骤 2 [阶段B前置]：purge stale 路由（collect 中标记 _stale 的，以及子节点过期的）
        try:
            self._ensure_port_routing(comp_id)
            # clean input stale
            r_in = self._composites[comp_id]["_port_routing"].get("input", {}) or {}
            for p in list(r_in.keys()):
                if isinstance(r_in[p], dict) and r_in[p].get("_stale"):
                    r_in[p] = {"source_output_path": "", "target_node": "", "target_port": "default"}
            r_out = self._composites[comp_id]["_port_routing"].get("output", {}) or {}
            for p in list(r_out.keys()):
                if isinstance(r_out[p], dict) and r_out[p].get("_stale"):
                    r_out[p] = {"target_composite": "", "target_node": "", "target_port": "default"}
        except Exception:
            pass

        # ── 隐藏复合节点 + 展开内部节点 UI（纯几何，不动边对象） ──
        comp_item.setVisible(False)
        comp_item.is_expanded = True
        self._canvas._batch_updating = True
        child_items = []
        try:
            for n in node_names:
                item = self._canvas.nodes.get(n)
                if item:
                    pos = positions.get(n, {"x": 0, "y": 0})
                    item.setPos(comp_pos.get("x", 0) + pos.get("x", 0), comp_pos.get("y", 0) + pos.get("y", 0))
                    item.setVisible(True)
                    child_items.append(item)
        finally:
            self._canvas._batch_updating = False
        logger.info(
            "[MORPH-EXPAND-SUMMARY] comp=%s UI-layout: visible_internal_nodes=%d frame=%s",
            comp_id,
            len(child_items),
            f"__frame__{comp_id}",
        )

        # ── 恢复内部连线（展开前折叠隐藏过的内部边） ──
        internal_restored = 0
        for info in comp.get("_internal_edges", []):
            for edge in self._canvas.edges:
                src_name = edge.start_node.node_name if hasattr(edge.start_node, "node_name") else ""
                tgt_name = edge.end_node.node_name if hasattr(edge.end_node, "node_name") else ""
                if src_name == info["src"] and tgt_name == info["tgt"]:
                    edge.setVisible(True)
                    edge.update_path()
                    internal_restored += 1
                    break
        logger.info("[MORPH-EXPAND-SUMMARY] comp=%s internal_edges restored=%d", comp_id, internal_restored)

        # 建立 group frame
        from ui.canvas.items.composite_group_frame import CompositeGroupFrame

        frame = CompositeGroupFrame(
            comp_id=comp_id, display_name=comp.get("display_name", ""), child_items=child_items, composite_manager=self
        )
        self._canvas.scene.addItem(frame)
        self._canvas.nodes[f"__frame__{comp_id}"] = frame

        # ── 步骤 3：undo macro + RouteCache 事务开始（保持 create_edge/remove_edge inside macro）
        undo_stack = None
        if self._canvas and getattr(self._canvas, "parent_window", None):
            undo_stack = getattr(self._canvas.parent_window, "undo_stack", None)
        import importlib

        qundo_stack_mod = None
        try:
            qundo_stack_mod = importlib.import_module("PySide6.QtWidgets").QUndoStack
        except Exception:
            pass
        if undo_stack and qundo_stack_mod and isinstance(undo_stack, qundo_stack_mod):
            undo_stack.beginMacro(f"Expand composite {comp_id}")
            in_macro = True
        else:
            in_macro = False
        logger.info("[MORPH-EXPAND-SUMMARY] comp=%s TX-begin: undo_macro=%s RouteCache.begin()", comp_id, in_macro)

        # RouteCache.begin
        from ui.core.edge.edge_config_writer import RouteCache, edge_config_writer

        RouteCache.begin()

        try:
            # ── 步骤 4 [阶段B：全删]：morph_list 对应的 old_edge（external↔comp）全部 remove_edge；
            #    RouteCache 同步清 composite 端对应路由（用 _morph_skip_config=True，因为下面手动写 RouteCache）
            canvas_connections = self._canvas
            # 收集当前所有连接 comp_item 的外部边（→对应 morph_list 的 old_edge）
            old_edges_to_remove = []
            for edge in list(self._canvas.edges):
                if edge.start_node is comp_item or edge.end_node is comp_item:
                    old_edges_to_remove.append(edge)
            for old_edge in old_edges_to_remove:
                try:
                    canvas_connections.remove_edge(
                        old_edge,
                        _from_morph=True,
                        _skip_undo_push=in_macro,
                        _morph_skip_config=True,
                    )
                except Exception as e:
                    logger.error("[MORPH-EXPAND-REMOVE-FAILED] edge=%s err=%s", old_edge, e)
            logger.info(
                "[MORPH-EXPAND-SUMMARY] comp=%s PhaseB-REMOVE old_comp_edges=%d (disconnected from composite)\n"
                "  old_edges_details=%s",
                comp_id,
                len(old_edges_to_remove),
                [
                    {
                        "start": (e.start_node.node_name if hasattr(e.start_node, "node_name") else None),
                        "end": (e.end_node.node_name if hasattr(e.end_node, "node_name") else None),
                        "sp": (e.source_anchor.port_name if hasattr(e, "source_anchor") and e.source_anchor else None),
                        "ep": (e.end_anchor.port_name if hasattr(e, "end_anchor") and e.end_anchor else None),
                    }
                    for e in old_edges_to_remove
                ],
            )

            # RouteCache：同步清空 composite.input/output 对应 in_port/out_port
            # （expand 目标是 comp 路由清空、child 有值 — 互斥态的 expanded=True）
            cleared_comp_ports_in = 0
            cleared_comp_ports_out = 0
            self._ensure_port_routing(comp_id)
            mem_routing = self._composites[comp_id]["_port_routing"]
            for item in morph_list:
                if item["direction"] == "input":
                    in_port = item.get("in_port") or ""
                    if in_port:
                        edge_config_writer.clear_by_kind(
                            kind="composite_input_routing",
                            cfg_path=str(self._comp_cfg_path(comp_id)),
                            comp_id=comp_id,
                            port=in_port,
                        )
                        # ── 内存同步：立刻清空，保证断言（flush 前）读内存也是空 ──
                        if in_port in (mem_routing.get("input") or {}):
                            del mem_routing["input"][in_port]
                        elif "data" in mem_routing["input"] and in_port == "default":
                            del mem_routing["input"]["data"]
                        elif "default" in mem_routing["input"] and in_port == "data":
                            del mem_routing["input"]["default"]
                        cleared_comp_ports_in += 1
                else:  # output
                    out_port = item.get("out_port") or ""
                    if out_port:
                        edge_config_writer.clear_by_kind(
                            kind="composite_output_routing",
                            cfg_path=str(self._comp_cfg_path(comp_id)),
                            comp_id=comp_id,
                            port=out_port,
                        )
                        # ── 内存同步：立刻清空 ──
                        if out_port in (mem_routing.get("output") or {}):
                            del mem_routing["output"][out_port]
                        cleared_comp_ports_out += 1
            logger.info(
                "[MORPH-EXPAND-SUMMARY] comp=%s PhaseB-ROUTE-CLEAR input_ports=%d output_ports=%d",
                comp_id,
                cleared_comp_ports_in,
                cleared_comp_ports_out,
            )

            # ── 步骤 5 [阶段C：全建]：用 morph_list 里抄好的 upstream_node_id/upstream_out_port/
            #    target_child/... 新建 external↔child 新边；create_edge 内部原子写 child listen/port_mappings
            new_edge_count = 0
            create_ok_input = 0
            create_ok_output = 0
            create_skip = 0
            create_fail = 0
            canvas_connections = self._canvas
            for item in morph_list:
                try:
                    if item["direction"] == "input":
                        up_node_name = item.get("upstream_node_id") or ""
                        up_port = item.get("upstream_out_port", "default") or "default"
                        tgt_child_name = item.get("target_child_name") or ""
                        tgt_child_port = item.get("target_child_port", "default") or "default"
                        if not up_node_name or not tgt_child_name:
                            logger.warning(
                                "[MORPH-EXPAND-CREATE] skip input: required empty up=%s tgt=%s item=%s",
                                up_node_name,
                                tgt_child_name,
                                item,
                            )
                            create_skip += 1
                            continue
                        src_item = canvas_connections.nodes.get(up_node_name)
                        dst_item = canvas_connections.nodes.get(tgt_child_name)
                        # ── 断言日志 + AnchorItem 解析（必须对象而不是字符串 port 名！）
                        #    统一走 anchor_manager：NodeItem/CompositeNodeItem 的锚点都挂在
                        #    node.anchor_manager.input_anchors/output_anchors 下，初始化时就有 default，
                        #    读取不存在的 NodeItem.output_anchors 属性会得到空 dict → 误报 anchor_exists=False。
                        src_has_node_attr = getattr(src_item, "node_name", None) == up_node_name if src_item else False
                        dst_has_node_attr = (
                            getattr(dst_item, "node_name", None) == tgt_child_name if dst_item else False
                        )
                        src_anchor_mgr = getattr(src_item, "anchor_manager", None)
                        dst_anchor_mgr = getattr(dst_item, "anchor_manager", None)
                        src_all_out: dict = {}
                        dst_all_in: dict = {}
                        if src_anchor_mgr is not None:
                            src_all_out = getattr(src_anchor_mgr, "output_anchors", {}) or {}
                        if dst_anchor_mgr is not None:
                            dst_all_in = getattr(dst_anchor_mgr, "input_anchors", {}) or {}
                        # backward compat：极少数旧节点没有 anchor_manager，仍然走属性 dict
                        if (
                            not src_all_out
                            and hasattr(src_item, "output_anchors")
                            and isinstance(src_item.output_anchors, dict)
                        ):
                            src_all_out = src_item.output_anchors
                        if (
                            not dst_all_in
                            and hasattr(dst_item, "input_anchors")
                            and isinstance(dst_item.input_anchors, dict)
                        ):
                            dst_all_in = dst_item.input_anchors
                        src_anchor_obj = None
                        dst_anchor_obj = None
                        if src_anchor_mgr is not None and callable(getattr(src_anchor_mgr, "get_output", None)):
                            src_anchor_obj = src_anchor_mgr.get_output(up_port)
                        elif up_port in src_all_out:
                            src_anchor_obj = src_all_out[up_port]
                        if dst_anchor_mgr is not None and callable(getattr(dst_anchor_mgr, "get_input", None)):
                            dst_anchor_obj = dst_anchor_mgr.get_input(tgt_child_port)
                        elif tgt_child_port in dst_all_in:
                            dst_anchor_obj = dst_all_in[tgt_child_port]
                        pw = getattr(canvas_connections, "parent_window", None)
                        tgt_in_nodes_data = tgt_child_name in getattr(pw, "nodes_data", {}) if pw else "<no-pw>"
                        logger.info(
                            "[MORPH-EXPAND-CREATE] direction=input\n"
                            "  - up=%s | src_item_exists=%s node_name_match=%s output_anchors.keys=%s | selected up_port=%s anchor_exists=%s\n"
                            "  - child=%s | dst_item_exists=%s node_name_match=%s in_nodes_data=%s input_anchors.keys=%s | selected tgt_port=%s anchor_exists=%s",
                            up_node_name,
                            src_item is not None,
                            src_has_node_attr,
                            list(src_all_out.keys()),
                            up_port,
                            src_anchor_obj is not None,
                            tgt_child_name,
                            dst_item is not None,
                            dst_has_node_attr,
                            tgt_in_nodes_data,
                            list(dst_all_in.keys()),
                            tgt_child_port,
                            dst_anchor_obj is not None,
                        )
                        if not src_item or not dst_item:
                            logger.error(
                                "[MORPH-EXPAND-CREATE] input FAILED: src_item=%s dst_item=%s",
                                src_item is not None,
                                dst_item is not None,
                            )
                            create_fail += 1
                            continue
                        created = canvas_connections.create_edge(
                            src_item,
                            dst_item,
                            target_anchor=dst_anchor_obj,  # AnchorItem！
                            source_anchor=src_anchor_obj,  # AnchorItem！
                            _from_morph=True,
                            _skip_undo_push=in_macro,
                        )
                        if created:
                            new_edge_count += 1
                            create_ok_input += 1
                        else:
                            create_fail += 1
                    else:  # output
                        child_src_name = item.get("source_child_name") or item.get("child_source_name") or ""
                        child_src_port = (
                            item.get("source_child_out_port") or item.get("child_source_port", "default") or "default"
                        )
                        dn_node_name = item.get("external_target_name") or item.get("downstream_node_id") or ""
                        dn_in_port = (
                            item.get("external_target_in_port")
                            or item.get("downstream_in_port", "default")
                            or "default"
                        )
                        if not child_src_name or not dn_node_name:
                            logger.warning(
                                "[MORPH-EXPAND-CREATE] skip output: required empty child=%s dn=%s item=%s",
                                child_src_name,
                                dn_node_name,
                                item,
                            )
                            create_skip += 1
                            continue
                        src_item = canvas_connections.nodes.get(child_src_name)
                        dst_item = canvas_connections.nodes.get(dn_node_name)
                        src_has_node_attr = (
                            getattr(src_item, "node_name", None) == child_src_name if src_item else False
                        )
                        dst_has_node_attr = getattr(dst_item, "node_name", None) == dn_node_name if dst_item else False
                        src_anchor_mgr = getattr(src_item, "anchor_manager", None)
                        dst_anchor_mgr = getattr(dst_item, "anchor_manager", None)
                        src_all_out: dict = {}
                        dst_all_in: dict = {}
                        if src_anchor_mgr is not None:
                            src_all_out = getattr(src_anchor_mgr, "output_anchors", {}) or {}
                        if dst_anchor_mgr is not None:
                            dst_all_in = getattr(dst_anchor_mgr, "input_anchors", {}) or {}
                        if (
                            not src_all_out
                            and hasattr(src_item, "output_anchors")
                            and isinstance(src_item.output_anchors, dict)
                        ):
                            src_all_out = src_item.output_anchors
                        if (
                            not dst_all_in
                            and hasattr(dst_item, "input_anchors")
                            and isinstance(dst_item.input_anchors, dict)
                        ):
                            dst_all_in = dst_item.input_anchors
                        src_anchor_obj = None
                        dst_anchor_obj = None
                        if src_anchor_mgr is not None and callable(getattr(src_anchor_mgr, "get_output", None)):
                            src_anchor_obj = src_anchor_mgr.get_output(child_src_port)
                        elif child_src_port in src_all_out:
                            src_anchor_obj = src_all_out[child_src_port]
                        if dst_anchor_mgr is not None and callable(getattr(dst_anchor_mgr, "get_input", None)):
                            dst_anchor_obj = dst_anchor_mgr.get_input(dn_in_port)
                        elif dn_in_port in dst_all_in:
                            dst_anchor_obj = dst_all_in[dn_in_port]
                        pw = getattr(canvas_connections, "parent_window", None)
                        child_in_nodes_data = child_src_name in getattr(pw, "nodes_data", {}) if pw else "<no-pw>"
                        logger.info(
                            "[MORPH-EXPAND-CREATE] direction=output\n"
                            "  - child=%s | src_item_exists=%s node_name_match=%s in_nodes_data=%s output_anchors.keys=%s | selected child_out_port=%s anchor_exists=%s\n"
                            "  - external=%s | dst_item_exists=%s node_name_match=%s input_anchors.keys=%s | selected external_in_port=%s anchor_exists=%s",
                            child_src_name,
                            src_item is not None,
                            src_has_node_attr,
                            child_in_nodes_data,
                            list(src_all_out.keys()),
                            child_src_port,
                            src_anchor_obj is not None,
                            dn_node_name,
                            dst_item is not None,
                            dst_has_node_attr,
                            list(dst_all_in.keys()),
                            dn_in_port,
                            dst_anchor_obj is not None,
                        )
                        if not src_item or not dst_item:
                            logger.error(
                                "[MORPH-EXPAND-CREATE] output FAILED: src_item=%s dst_item=%s",
                                src_item is not None,
                                dst_item is not None,
                            )
                            create_fail += 1
                            continue
                        created = canvas_connections.create_edge(
                            src_item,
                            dst_item,
                            target_anchor=dst_anchor_obj,  # AnchorItem！
                            source_anchor=src_anchor_obj,  # AnchorItem！
                            _from_morph=True,
                            _skip_undo_push=in_macro,
                        )
                        if created:
                            new_edge_count += 1
                            create_ok_output += 1
                        else:
                            create_fail += 1
                except Exception as e:
                    logger.error("[MORPH-EXPAND-CREATE-FAILED] item=%s err=%s", item, e, exc_info=True)
                    create_fail += 1

            logger.info(
                "[MORPH-EXPAND-SUMMARY] comp=%s PhaseC-CREATE total_requested=%d "
                "ok=%d (input_ok=%d output_ok=%d) skip=%d fail=%d\n"
                "  new_edges=%d",
                comp_id,
                len(morph_list),
                create_ok_input + create_ok_output,
                create_ok_input,
                create_ok_output,
                create_skip,
                create_fail,
                new_edge_count,
            )

            # ── 批量更新内部节点连线路径（一次到位）
            self._batch_update_edges_for_nodes(node_names)

            # ── 步骤 6：RouteCache.flush（原子写所有配置到磁盘）
            # 必须放在互斥断言之前！否则断言读磁盘时还是旧值导致误报。
            flushed = RouteCache.flush()
            logger.info("[MORPH-EXPAND-SUMMARY] comp=%s PhaseD-FLUSH flushed_cfgs=%d", comp_id, flushed)

            # ── 步骤 5.5：互斥硬断言（expand 后必须 expanded=True 一致）
            # 注意：放在 flush 之后断言，确保磁盘上已经是 RouteCache 写出的最新值。
            # 断言失败不再 rollback（因为已经 flush 写盘，rollback 无法恢复），仅 ERROR 记录。
            mutex_assertion_ok = True
            try:
                self._assert_mutex_consistency(comp_id, morph_list, expanded=True)
            except AssertionError as ae:
                mutex_assertion_ok = False
                logger.error(
                    "[MORPH-MUTEX-FAILED-EXPAND] %s (RouteCache already flushed=%d, skip rollback)",
                    ae,
                    flushed,
                    exc_info=True,
                )
                if in_macro:
                    try:
                        undo_stack.setActive(False)
                        undo_stack.setActive(True)
                    except Exception:
                        pass
            finally:
                logger.info("[MORPH-EXPAND-SUMMARY] comp=%s mutex_assertion=%s", comp_id, mutex_assertion_ok)

        finally:
            if in_macro and undo_stack is not None:
                try:
                    undo_stack.endMacro()
                except Exception:
                    pass

        # 持久化 comp 状态
        comp["_expanded"] = True
        comp["_child_items"] = node_names
        self.save()
        # 写入 composite.json（external_connections 同步）
        comp_cfg = self._load_composite_config(comp_id)
        if comp_cfg:
            comp_cfg["external_connections"] = self._get_port_routing(comp_id)
            self._write_composite_config(comp_id, comp_cfg)
        logger.info(
            "[MORPH-EXPAND-SUMMARY] ==== EXPAND END comp=%s expanded=now-True composite.json_saved=%s",
            comp_id,
            comp_cfg is not None,
        )

        # ── Phase3 灰度：并行调用统一状态机 expand（差异告警，不影响主流程）
        self._gray_expand(comp_id)

    def _collapse_composite(self, comp_id: str, comp_item):
        """Collapse composite: 三阶段严格分离（先收集→再删→后建）。

        USE_MORPH_MUTEX_SWITCH=False → 回退旧的 anchor-morph 平移（开发期兜底）。
        """
        comp = self._composites.get(comp_id) or {}
        logger.info(
            "[MORPH-COLLAPSE-SUMMARY] ==== COLLAPSE START comp=%s USE_MORPH_MUTEX_SWITCH=%s "
            "manager._expanded=%s comp_item.is_expanded=%s scene_exists=%s",
            comp_id,
            USE_MORPH_MUTEX_SWITCH,
            comp.get("_expanded", False),
            getattr(comp_item, "is_expanded", None),
            comp_item.scene() is not None,
        )
        if not comp:
            logger.info("[MORPH-COLLAPSE-SUMMARY] comp=%s ABORT: comp not in _composites", comp_id)
            return
        node_names = list(comp.get("nodes", []) or [])
        logger.info("[MORPH-COLLAPSE-SUMMARY] comp=%s internal_nodes=%d nodes=%s", comp_id, len(node_names), node_names)

        # ── 防错：展开态单入口 DAG 校验 ──
        node_set = set(node_names)
        edges_list = []
        for edge_item in self._canvas.edges:
            src = edge_item.start_node.node_name if hasattr(edge_item.start_node, "node_name") else ""
            tgt = edge_item.end_node.node_name if hasattr(edge_item.end_node, "node_name") else ""
            if src in node_set and tgt in node_set:
                edges_list.append({"from": src, "to": tgt})
        nodes_data = self._canvas.parent_window.nodes_data if self._canvas.parent_window else {}
        is_valid, err_msg = self._validate_dag_single_entry(node_names, edges_list, nodes_data)
        if not is_valid:
            themed_message(None, t(TK.COMPOSITE_COLLAPSE_BLOCKED_TITLE), err_msg, "warning")
            logger.warning("collapse blocked for %s: %s", comp_id, err_msg)
            logger.info("[MORPH-COLLAPSE-SUMMARY] comp=%s ABORT: DAG single-entry check fail: %s", comp_id, err_msg)
            return

        comp_pos = comp.get("canvas_position", {"x": 0, "y": 0})

        # ── 灰度开关回退：旧 anchor-morph 平移实现 ──
        if not USE_MORPH_MUTEX_SWITCH:
            logger.info("[MORPH-COLLAPSE-SUMMARY] comp=%s ROUTE: OLD fallback anchor-morph", comp_id)
            for n in node_names:
                item = self._canvas.nodes.get(n)
                if item and item.isVisible():
                    comp["original_positions"][n] = {
                        "x": item.pos().x() - comp_pos.get("x", 0),
                        "y": item.pos().y() - comp_pos.get("y", 0),
                    }
                    item.setVisible(False)
            node_set = set(node_names)
            internal_edge_info = []
            for edge in self._canvas.edges:
                src_name = edge.start_node.node_name if hasattr(edge.start_node, "node_name") else ""
                tgt_name = edge.end_node.node_name if hasattr(edge.end_node, "node_name") else ""
                if src_name in node_set and tgt_name in node_set:
                    if edge.isVisible():
                        internal_edge_info.append(
                            {
                                "src": src_name,
                                "tgt": tgt_name,
                                "src_port": getattr(edge, "source_port_name", ""),
                                "tgt_port": getattr(edge, "target_port_name", ""),
                            }
                        )
                    edge.setVisible(False)
            comp["_internal_edges"] = internal_edge_info
            comp_cfg = self._load_composite_config(comp_id)
            if comp_cfg:
                comp_cfg["edges"] = [
                    {
                        "from": e["src"],
                        "to": e["tgt"],
                        "source_port": e.get("src_port", ""),
                        "target_port": e.get("tgt_port", ""),
                    }
                    for e in internal_edge_info
                ]
            frame_key = f"__frame__{comp_id}"
            frame = self._canvas.nodes.pop(frame_key, None)
            if frame and frame.scene():
                frame.scene().removeItem(frame)
            comp_item.setVisible(True)
            comp_item.is_expanded = False
            self._morph_internal_to_composite_edges(comp_id, comp_item, node_names)
            self._refresh_ports_on_collapse(comp_id, comp_item, node_names)
            if comp_cfg:
                comp_cfg["ports"] = {
                    "input": comp.get("input_ports", []),
                    "output": comp.get("output_ports", []),
                }
            new_rules = self._extract_entry_filter_rules(node_names, edges_list, nodes_data)
            if new_rules and comp_cfg:
                comp["input_filter_rules"] = new_rules
                comp_cfg["input_filter_rules"] = new_rules
            if comp_cfg:
                comp_cfg["external_connections"] = self._get_port_routing(comp_id)
                self._write_composite_config(comp_id, comp_cfg)
                self._sync_pipeline(comp_id)
                self._touch_pipe_signal(comp_id)
            comp["_expanded"] = False
            self.save()
            self._gray_collapse(comp_id)
            return

        logger.info("[MORPH-COLLAPSE-SUMMARY] comp=%s ROUTE: NEW 3-phase morph mutex", comp_id)

        # ═══════════════════════════════════════════════════════════════════
        # Phase4.1 新机制：6 步三阶段严格分离（修 Bug D/F/G）
        # ═══════════════════════════════════════════════════════════════════

        # ── 步骤 1 [阶段A 只读收集]：在所有子节点配置/UI 边完好时抄 morph_list
        morph_list = self.collect_collapse_morph_list(comp_id)
        input_cnt = sum(1 for it in morph_list if it.get("direction") == "input")
        output_cnt = sum(1 for it in morph_list if it.get("direction") == "output")
        logger.info(
            "[MORPH-COLLAPSE-SUMMARY] comp=%s PhaseA-COLLECT total=%d (input=%d output=%d)\n  morph_list_keys=%s",
            comp_id,
            len(morph_list),
            input_cnt,
            output_cnt,
            [{k: v for k, v in it.items() if k != "_stale"} for it in morph_list],
        )

        # ── 保存当前子节点相对位置，隐藏内部节点（纯几何，不动边对象）
        for n in list(node_names):
            item = self._canvas.nodes.get(n)
            if item and item.isVisible():
                comp["original_positions"][n] = {
                    "x": item.pos().x() - comp_pos.get("x", 0),
                    "y": item.pos().y() - comp_pos.get("y", 0),
                }
                item.setVisible(False)

        # ── 隐藏内部边 + 记录 internal_edges（用于下次 expand 恢复显示）
        internal_edge_info = []
        for edge in self._canvas.edges:
            src_name = edge.start_node.node_name if hasattr(edge.start_node, "node_name") else ""
            tgt_name = edge.end_node.node_name if hasattr(edge.end_node, "node_name") else ""
            if src_name in node_set and tgt_name in node_set:
                if edge.isVisible():
                    internal_edge_info.append(
                        {
                            "src": src_name,
                            "tgt": tgt_name,
                            "src_port": getattr(edge, "source_port_name", ""),
                            "tgt_port": getattr(edge, "target_port_name", ""),
                        }
                    )
                edge.setVisible(False)
        comp["_internal_edges"] = internal_edge_info
        logger.info(
            "[MORPH-COLLAPSE-SUMMARY] comp=%s internal_edges=%d nodes_hidden=%d",
            comp_id,
            len(internal_edge_info),
            len(node_names),
        )

        # 同步 DAG 拓扑到 composite.cfg
        comp_cfg = self._load_composite_config(comp_id)
        if comp_cfg:
            comp_cfg["edges"] = [
                {
                    "from": e["src"],
                    "to": e["tgt"],
                    "source_port": e.get("src_port", ""),
                    "target_port": e.get("tgt_port", ""),
                }
                for e in internal_edge_info
            ]

        # 移除 group frame
        frame_key = f"__frame__{comp_id}"
        frame = self._canvas.nodes.pop(frame_key, None)
        if frame and frame.scene():
            frame.scene().removeItem(frame)

        # 显示复合节点
        comp_item.setVisible(True)
        comp_item.is_expanded = False
        logger.info(
            "[MORPH-COLLAPSE-SUMMARY] comp=%s UI layout: comp now Visible frame_removed=%s", comp_id, frame is not None
        )

        # 先确保 comp_item.anchors 已刷新（按收集阶段新建的 comp_in_port 等端口去更新锚点）
        self._ensure_comp_anchors_refreshed(comp_item, comp_id)

        # ── 步骤 3：undo macro + RouteCache 事务开始
        undo_stack = None
        if self._canvas and getattr(self._canvas, "parent_window", None):
            undo_stack = getattr(self._canvas.parent_window, "undo_stack", None)
        import importlib

        qundo_stack_mod = None
        try:
            qundo_stack_mod = importlib.import_module("PySide6.QtWidgets").QUndoStack
        except Exception:
            pass
        if undo_stack and qundo_stack_mod and isinstance(undo_stack, qundo_stack_mod):
            undo_stack.beginMacro(f"Collapse composite {comp_id}")
            in_macro = True
        else:
            in_macro = False
        logger.info("[MORPH-COLLAPSE-SUMMARY] comp=%s TX-begin: undo_macro=%s RouteCache.begin()", comp_id, in_macro)

        from ui.core.edge.edge_config_writer import RouteCache, edge_config_writer

        RouteCache.begin()

        try:
            # ── 步骤 4 [阶段B：全删]：morph_list 对应的 external↔child 旧边全部 remove_edge
            #    用 _morph_skip_config=True，RouteCache 写由这里统一做
            canvas_connections = self._canvas
            edges_removed = 0
            edges_checked = 0

            # 先从 morph_list 收集所有 old_edge：起点/终点在 node_set 里的边（external↔child）
            details_removed = []
            for edge in list(self._canvas.edges):
                edges_checked += 1
                src_name = edge.start_node.node_name if hasattr(edge.start_node, "node_name") else ""
                tgt_name = edge.end_node.node_name if hasattr(edge.end_node, "node_name") else ""
                src_in = src_name in node_set
                tgt_in = tgt_name in node_set
                if (src_in and not tgt_in) or (not src_in and tgt_in):
                    logger.info(
                        "[MORPH-COLLAPSE-REMOVE] will remove edge %s->%s (src_in=%s tgt_in=%s)",
                        src_name,
                        tgt_name,
                        src_in,
                        tgt_in,
                    )
                    try:
                        details_removed.append(
                            {
                                "start": src_name,
                                "end": tgt_name,
                                "sp": (
                                    edge.source_anchor.port_name
                                    if hasattr(edge, "source_anchor") and edge.source_anchor
                                    else None
                                ),
                                "ep": (
                                    edge.end_anchor.port_name
                                    if hasattr(edge, "end_anchor") and edge.end_anchor
                                    else None
                                ),
                            }
                        )
                        canvas_connections.remove_edge(
                            edge,
                            _from_morph=True,
                            _skip_undo_push=in_macro,
                            _morph_skip_config=True,
                        )
                        edges_removed += 1
                    except Exception as e:
                        logger.error("[MORPH-COLLAPSE-REMOVE-FAILED] edge err=%s", e)
                else:
                    logger.debug(
                        "[MORPH-COLLAPSE-KEEP-EDGE] skip %s->%s (src_in=%s tgt_in=%s node_set_size=%d)",
                        src_name,
                        tgt_name,
                        src_in,
                        tgt_in,
                        len(node_set),
                    )
            logger.info(
                "[MORPH-COLLAPSE-SUMMARY] comp=%s PhaseB-REMOVE checked=%d removed=%d\n  removed_details=%s",
                comp_id,
                edges_checked,
                edges_removed,
                details_removed,
            )

            # RouteCache：手动清 child listen_upper_file / port_mappings / out_connections
            # （collapse 目标：child 清空、comp 端口有值 — 互斥态 expanded=False）
            cleared_child_cfgs_in = 0
            cleared_child_cfgs_out = 0
            nodes_data_global = self._nodes_data_global()
            parent_window = getattr(self._canvas, "parent_window", None)
            for item in morph_list:
                if item["direction"] == "input":
                    tgt_child = item.get("target_child_name") or ""
                    tgt_child_port = item.get("target_child_port", "default") or "default"
                    if not tgt_child:
                        continue
                    child_cfg_path = str(Path(get_config_path(str(Path(self._project_path) / "nodes" / tgt_child))))
                    if tgt_child_port == "default":
                        edge_config_writer.clear_by_kind(
                            kind="listen_upper_file",
                            cfg_path=child_cfg_path,
                        )
                    else:
                        edge_config_writer.clear_by_kind(
                            kind="port_mapping",
                            cfg_path=child_cfg_path,
                            port=tgt_child_port,
                        )
                    # ── 原子写磁盘：断言在 flush 前读磁盘，所以立刻清空 ──
                    try:
                        p = Path(child_cfg_path)
                        if p.exists():
                            with p.open(encoding="utf-8") as f:
                                ccfg = json.load(f) or {}
                        else:
                            ccfg = {}
                        changed = False
                        if tgt_child_port == "default":
                            if ccfg.get("listen_upper_file"):
                                ccfg["listen_upper_file"] = ""
                                changed = True
                        else:
                            pm = ccfg.get("port_mappings", {}) or {}
                            if pm.get(tgt_child_port):
                                pm[tgt_child_port] = ""
                                ccfg["port_mappings"] = pm
                                changed = True
                        if changed:
                            with p.open("w", encoding="utf-8") as f:
                                json.dump(ccfg, f, indent=2, ensure_ascii=False)
                            # 同步内存 nodes_data
                            if tgt_child in nodes_data_global:
                                nodes_data_global[tgt_child]["config"] = ccfg
                            if parent_window and hasattr(parent_window, "nodes_data"):
                                if tgt_child in parent_window.nodes_data:
                                    parent_window.nodes_data[tgt_child]["config"] = ccfg
                    except Exception as e:
                        logger.warning(
                            "[MORPH-COLLAPSE] input: child=%s port=%s immediate disk-clear failed: %s",
                            tgt_child,
                            tgt_child_port,
                            e,
                        )
                    cleared_child_cfgs_in += 1
                else:  # output
                    child_src = item.get("source_child_name") or item.get("child_source_name") or ""
                    child_src_port = (
                        item.get("source_child_out_port") or item.get("child_source_port", "default") or "default"
                    )
                    if not child_src:
                        continue
                    # ── out_connections 对应 src_port 立刻清磁盘（L3871-3888 断言读磁盘） ──
                    child_cfg_path = str(Path(get_config_path(str(Path(self._project_path) / "nodes" / child_src))))
                    try:
                        p = Path(child_cfg_path)
                        if p.exists():
                            with p.open(encoding="utf-8") as f:
                                ccfg = json.load(f) or {}
                        else:
                            ccfg = {}
                        oc = ccfg.get("out_connections", {}) or {}
                        if oc.get(child_src_port):
                            oc[child_src_port] = ""
                            ccfg["out_connections"] = oc
                            with p.open("w", encoding="utf-8") as f:
                                json.dump(ccfg, f, indent=2, ensure_ascii=False)
                            # 同步内存 nodes_data
                            if child_src in nodes_data_global:
                                nodes_data_global[child_src]["config"] = ccfg
                            if parent_window and hasattr(parent_window, "nodes_data"):
                                if child_src in parent_window.nodes_data:
                                    parent_window.nodes_data[child_src]["config"] = ccfg
                    except Exception as e:
                        logger.warning(
                            "[MORPH-COLLAPSE] output: child=%s port=%s out_connections clear failed: %s",
                            child_src,
                            child_src_port,
                            e,
                        )
                    cleared_child_cfgs_out += 1
                    # create_edge 会写入 comp.out_port → downstream 的 composite_output_routing
            logger.info(
                "[MORPH-COLLAPSE-SUMMARY] comp=%s PhaseB-ROUTE-CLEAR children input=%d output=%d",
                comp_id,
                cleared_child_cfgs_in,
                cleared_child_cfgs_out,
            )

            # ── 步骤 5 [阶段C：全建]：根据 morph_list 新建 external↔comp 新边
            #    create_edge 内部会自动写 composite_input_routing / composite_output_routing
            new_edge_count = 0
            create_ok_input = 0
            create_ok_output = 0
            create_skip = 0
            create_fail = 0
            for item in morph_list:
                try:
                    if item["direction"] == "input":
                        up_node_name = item.get("upstream_node_id") or ""
                        up_out_port = item.get("upstream_out_port", "default") or "default"
                        comp_in_port = item.get("comp_in_port") or ""
                        if not up_node_name or not comp_in_port:
                            logger.warning(
                                "[MORPH-COLLAPSE-CREATE] skip input: up=%s comp_in=%s item=%s",
                                up_node_name,
                                comp_in_port,
                                item,
                            )
                            create_skip += 1
                            continue
                        src_item = self._canvas.nodes.get(up_node_name)
                        if not src_item or comp_item.scene() is None:
                            logger.error(
                                "[MORPH-COLLAPSE-CREATE] input skip src_item=%s comp_item.scene_ok=%s",
                                src_item is not None,
                                comp_item.scene() is not None,
                            )
                            create_fail += 1
                            continue
                        # AnchorItem 解析（必须对象不能是字符串 port！）
                        # 统一走 anchor_manager：NodeItem/CompositeNodeItem 锚点都在 anchor_manager 下，
                        # 直接访问 node.output_anchors/node.input_anchors 属性可能为空。
                        src_anchor_mgr = getattr(src_item, "anchor_manager", None)
                        comp_anchor_mgr = getattr(comp_item, "anchor_manager", None)
                        src_all_out: dict = {}
                        comp_all_in: dict = {}
                        if src_anchor_mgr is not None:
                            src_all_out = getattr(src_anchor_mgr, "output_anchors", {}) or {}
                        if comp_anchor_mgr is not None:
                            comp_all_in = getattr(comp_anchor_mgr, "input_anchors", {}) or {}
                        # backward compat：无 anchor_manager 时退回属性 dict
                        if (
                            not src_all_out
                            and hasattr(src_item, "output_anchors")
                            and isinstance(src_item.output_anchors, dict)
                        ):
                            src_all_out = src_item.output_anchors
                        if (
                            not comp_all_in
                            and hasattr(comp_item, "input_anchors")
                            and isinstance(comp_item.input_anchors, dict)
                        ):
                            comp_all_in = comp_item.input_anchors
                        src_anchor_obj = None
                        comp_anchor_obj = None
                        if src_anchor_mgr is not None and callable(getattr(src_anchor_mgr, "get_output", None)):
                            src_anchor_obj = src_anchor_mgr.get_output(up_out_port)
                        elif up_out_port in src_all_out:
                            src_anchor_obj = src_all_out[up_out_port]
                        # 端口名映射：内存路由 key="data" → 实际渲染 anchor.port_name="default"
                        # （因为 CompositeNodeItem._create_anchors_from_ports 把 entry_port=data 的过滤掉了，
                        #  走 AnchorManager 默认 listen_upper_file 锚点）
                        cand_port = comp_in_port
                        if cand_port not in comp_all_in and cand_port in {"data"}:
                            cand_port = "default"
                        if comp_anchor_mgr is not None and callable(getattr(comp_anchor_mgr, "get_input", None)):
                            comp_anchor_obj = comp_anchor_mgr.get_input(cand_port)
                        elif cand_port in comp_all_in:
                            comp_anchor_obj = comp_all_in[cand_port]
                        src_name_ok = getattr(src_item, "node_name", None) == up_node_name if src_item else False
                        comp_in_anchors_keys = list(comp_all_in.keys())
                        src_out_keys = list(src_all_out.keys())
                        logger.info(
                            "[MORPH-COLLAPSE-CREATE] direction=input\n"
                            "  - up=%s | src_item_exists=%s node_name_match=%s output_anchors.keys=%s | selected up_out_port=%s anchor_exists=%s\n"
                            "  - comp=%s | comp_in_anchors.keys=%s | selected comp_in_port=%s(real=%s) anchor_exists=%s",
                            up_node_name,
                            src_item is not None,
                            src_name_ok,
                            src_out_keys,
                            up_out_port,
                            src_anchor_obj is not None,
                            comp_id,
                            comp_in_anchors_keys,
                            comp_in_port,
                            cand_port,
                            comp_anchor_obj is not None,
                        )
                        if comp_anchor_obj is None and isinstance(comp_all_in, dict) and comp_all_in:
                            # 终极兜底：取第一个 input 锚点（通常是 default）
                            for k in ("default", "data"):
                                if k in comp_all_in:
                                    comp_anchor_obj = comp_all_in[k]
                                    break
                            if comp_anchor_obj is None:
                                comp_anchor_obj = next(iter(comp_all_in.values()))
                        created = canvas_connections.create_edge(
                            src_item,
                            comp_item,
                            target_anchor=comp_anchor_obj,  # AnchorItem！
                            source_anchor=src_anchor_obj,  # AnchorItem！
                            _from_morph=True,
                            _skip_undo_push=in_macro,
                        )
                        if created:
                            new_edge_count += 1
                            create_ok_input += 1
                        else:
                            create_fail += 1
                    else:  # output
                        comp_out_port = item.get("comp_out_port") or ""
                        dn_node_name = item.get("external_target_name") or item.get("downstream_node_id") or ""
                        dn_in_port = (
                            item.get("external_target_in_port")
                            or item.get("downstream_in_port", "default")
                            or "default"
                        )
                        if not comp_out_port or not dn_node_name:
                            logger.warning(
                                "[MORPH-COLLAPSE-CREATE] skip output: comp_out=%s dn=%s item=%s",
                                comp_out_port,
                                dn_node_name,
                                item,
                            )
                            create_skip += 1
                            continue
                        dst_item = self._canvas.nodes.get(dn_node_name)
                        if not dst_item:
                            logger.error("[MORPH-COLLAPSE-CREATE] output skip dst_item=%s", dst_item is not None)
                            create_fail += 1
                            continue
                        # AnchorItem 解析（不能传字符串！）统一走 anchor_manager
                        comp_anchor_mgr = getattr(comp_item, "anchor_manager", None)
                        dst_anchor_mgr = getattr(dst_item, "anchor_manager", None)
                        comp_all_out: dict = {}
                        dst_all_in: dict = {}
                        if comp_anchor_mgr is not None:
                            comp_all_out = getattr(comp_anchor_mgr, "output_anchors", {}) or {}
                        if dst_anchor_mgr is not None:
                            dst_all_in = getattr(dst_anchor_mgr, "input_anchors", {}) or {}
                        # backward compat
                        if (
                            not comp_all_out
                            and hasattr(comp_item, "output_anchors")
                            and isinstance(comp_item.output_anchors, dict)
                        ):
                            comp_all_out = comp_item.output_anchors
                        if (
                            not dst_all_in
                            and hasattr(dst_item, "input_anchors")
                            and isinstance(dst_item.input_anchors, dict)
                        ):
                            dst_all_in = dst_item.input_anchors
                        comp_anchor_obj = None
                        dst_anchor_obj = None
                        # 端口名映射：路由里的 "*_out" / "node_*" / "node_output" →
                        # 实际渲染 anchor.port_name="default"（CompositeNodeItem._create_anchors_from_ports
                        # 里 L137 过滤掉 *_out 和 node_*，走 AnchorManager 默认 output_file 锚点）
                        cand_port = comp_out_port
                        if cand_port not in comp_all_out and (
                            cand_port.endswith("_out") or cand_port.startswith("node_") or cand_port == "node_output"
                        ):
                            cand_port = "default"
                        if comp_anchor_mgr is not None and callable(getattr(comp_anchor_mgr, "get_output", None)):
                            comp_anchor_obj = comp_anchor_mgr.get_output(cand_port)
                        elif cand_port in comp_all_out:
                            comp_anchor_obj = comp_all_out[cand_port]
                        if dst_anchor_mgr is not None and callable(getattr(dst_anchor_mgr, "get_input", None)):
                            dst_anchor_obj = dst_anchor_mgr.get_input(dn_in_port)
                        elif dn_in_port in dst_all_in:
                            dst_anchor_obj = dst_all_in[dn_in_port]
                        dst_name_ok = getattr(dst_item, "node_name", None) == dn_node_name if dst_item else False
                        comp_out_anchors_keys = list(comp_all_out.keys())
                        dst_in_anchors_keys = list(dst_all_in.keys())
                        logger.info(
                            "[MORPH-COLLAPSE-CREATE] direction=output\n"
                            "  - comp=%s | output_anchors.keys=%s | selected comp_out_port=%s(real=%s) anchor_exists=%s\n"
                            "  - external=%s | dst_item_exists=%s node_name_match=%s input_anchors.keys=%s | selected dn_in_port=%s anchor_exists=%s",
                            comp_id,
                            comp_out_anchors_keys,
                            comp_out_port,
                            cand_port,
                            comp_anchor_obj is not None,
                            dn_node_name,
                            dst_item is not None,
                            dst_name_ok,
                            dst_in_anchors_keys,
                            dn_in_port,
                            dst_anchor_obj is not None,
                        )
                        if comp_anchor_obj is None and isinstance(comp_all_out, dict) and comp_all_out:
                            # 终极兜底：取第一个输出锚点
                            for k in ("default", "node_output"):
                                if k in comp_all_out:
                                    comp_anchor_obj = comp_all_out[k]
                                    break
                            if comp_anchor_obj is None:
                                comp_anchor_obj = next(iter(comp_all_out.values()))
                        created = canvas_connections.create_edge(
                            comp_item,
                            dst_item,
                            target_anchor=dst_anchor_obj,  # AnchorItem！
                            source_anchor=comp_anchor_obj,  # AnchorItem！
                            _from_morph=True,
                            _skip_undo_push=in_macro,
                        )
                        if created:
                            new_edge_count += 1
                            create_ok_output += 1
                        else:
                            create_fail += 1
                except Exception as e:
                    logger.error("[MORPH-COLLAPSE-CREATE-FAILED] item=%s err=%s", item, e, exc_info=True)
                    create_fail += 1

            logger.info(
                "[MORPH-COLLAPSE-SUMMARY] comp=%s PhaseC-CREATE total_requested=%d "
                "ok=%d (input_ok=%d output_ok=%d) skip=%d fail=%d\n"
                "  new_edges=%d",
                comp_id,
                len(morph_list),
                create_ok_input + create_ok_output,
                create_ok_input,
                create_ok_output,
                create_skip,
                create_fail,
                new_edge_count,
            )

            # ── 步骤 6：RouteCache.flush（原子写所有配置到磁盘）
            # 必须放在互斥断言之前！否则断言读磁盘时还是旧值导致误报。
            flushed = RouteCache.flush()
            logger.info("[MORPH-COLLAPSE-SUMMARY] comp=%s PhaseD-FLUSH flushed_cfgs=%d", comp_id, flushed)

            # ── 步骤 5.5：互斥硬断言（collapse 后必须 expanded=False 一致）
            mutex_assertion_ok = True
            try:
                self._assert_mutex_consistency(comp_id, morph_list, expanded=False)
            except AssertionError as ae:
                mutex_assertion_ok = False
                logger.error(
                    "[MORPH-MUTEX-FAILED-COLLAPSE] %s (RouteCache already flushed=%d, skip rollback)",
                    ae,
                    flushed,
                    exc_info=True,
                )
                if in_macro:
                    try:
                        undo_stack.setActive(False)
                        undo_stack.setActive(True)
                    except Exception:
                        pass
            finally:
                logger.info("[MORPH-COLLAPSE-SUMMARY] comp=%s mutex_assertion=%s", comp_id, mutex_assertion_ok)

        finally:
            if in_macro and undo_stack is not None:
                try:
                    undo_stack.endMacro()
                except Exception:
                    pass

        # ── 同步端口定义 + 过滤规则 + pipeline ──
        if comp_cfg:
            comp_cfg["ports"] = {
                "input": comp.get("input_ports", []),
                "output": comp.get("output_ports", []),
            }
        new_rules = self._extract_entry_filter_rules(node_names, edges_list, nodes_data)
        if new_rules and comp_cfg:
            comp["input_filter_rules"] = new_rules
            comp_cfg["input_filter_rules"] = new_rules
        if comp_cfg:
            comp_cfg["external_connections"] = self._get_port_routing(comp_id)
            self._write_composite_config(comp_id, comp_cfg)
            self._sync_pipeline(comp_id)
            self._touch_pipe_signal(comp_id)

        comp["_expanded"] = False
        self.save()
        logger.info(
            "[MORPH-COLLAPSE-SUMMARY] ==== COLLAPSE END comp=%s expanded=now-False composite.json_saved=%s",
            comp_id,
            comp_cfg is not None,
        )

        # ── Phase3 灰度：并行调用统一状态机 collapse（差异告警）
        self._gray_collapse(comp_id)

    def _ensure_comp_anchors_refreshed(self, comp_item, comp_id: str) -> None:
        """collapse 阶段C前确保 comp_item 的 input/output 锚点按 comp.input_ports/output_ports 已存在。

        避免 create_edge(comp_in_port) 时找不到锚点。"""
        comp = self._composites.get(comp_id, {})
        input_ports = comp.get("input_ports", []) or []
        output_ports = comp.get("output_ports", []) or []
        try:
            updater = getattr(comp_item, "update_ports", None)
            if callable(updater):
                updater(input_ports, output_ports)
        except Exception as e:
            logger.warning("[MORPH-ANCHOR-REFRESH] comp=%s update_ports failed: %s", comp_id, e)

    def _comp_cfg_path(self, comp_id: str) -> Path:
        """返回 composite_${comp_id}.json 的绝对路径。"""
        return Path(self._project_path) / COMPOSITE_NODES_DIR / f"{comp_id}.json"

    def _refresh_ports_on_collapse(self, comp_id, comp_item, node_names):
        """Re-identify ports after collapse to reflect any changed connections.

        Also re-binds all composite-connected edges to the new anchors
        (since update_ports() destroys old anchors). Edges whose port_name
        no longer matches any new port are removed.
        """
        node_set = set(node_names)
        edges_list = []
        for edge_item in self._canvas.edges:
            src = edge_item.start_node.node_name if hasattr(edge_item.start_node, "node_name") else ""
            tgt = edge_item.end_node.node_name if hasattr(edge_item.end_node, "node_name") else ""
            if src in node_set and tgt in node_set:
                edges_list.append({"from": src, "to": tgt})

        # Save composite-connected edges before anchor destruction
        saved_edges = []
        for edge in list(self._canvas.edges):
            if edge.start_node is comp_item:
                port_name = getattr(getattr(edge, "_source_anchor", None), "port_name", "") or getattr(
                    edge, "_desired_source_port_name", ""
                )
                saved_edges.append({"edge": edge, "direction": "output", "port_name": port_name})
            elif edge.end_node is comp_item:
                port_name = getattr(getattr(edge, "_target_anchor", None), "port_name", "") or getattr(
                    edge, "_desired_target_port_name", ""
                )
                saved_edges.append({"edge": edge, "direction": "input", "port_name": port_name})

        nodes_data = self._canvas.parent_window.nodes_data if self._canvas.parent_window else {}

        # ── 刷新 nodes_data 中的 listen_upper_file ──
        # 折叠时，内部节点之间的监听关系由 DAG 编排器管理，不再需要 listen_upper_file。
        # 清除两种陈旧值：
        # 1. 指向复合节点外部节点的 listen（原逻辑）
        # 2. 指向复合节点内部节点的 listen（展开后重新连线导致入口变更）
        for n in node_names:
            nd = nodes_data.get(n, {})
            cfg = nd.get("config", {})
            if cfg:
                listen = cfg.get("listen_upper_file", "")
                if listen:
                    upstream = self._extract_node_from_path(listen)
                    if upstream:
                        # 不管是外部还是内部，折叠后统一清除
                        cfg["listen_upper_file"] = ""

        new_ports = self._identify_ports(node_names, edges_list, nodes_data)

        comp = self._composites.get(comp_id)
        if comp:
            comp["input_ports"] = new_ports.get("input_ports", [])
            comp["output_ports"] = new_ports.get("output_ports", [])

        comp_item.update_ports(new_ports.get("input_ports", []), new_ports.get("output_ports", []))

        # Re-bind saved edges to new anchors (or remove if port no longer exists)
        for info in saved_edges:
            edge = info["edge"]
            if info["direction"] == "output":
                new_anchor = comp_item.find_anchor_by_port(info["port_name"], "output")
                if new_anchor:
                    edge._source_anchor = new_anchor
                    edge.start_anchor = new_anchor  # sync public attr
                    edge.update_path()
                else:
                    # Port not found → fallback to node center connection
                    edge._source_anchor = None
                    edge.start_anchor = None  # sync public attr
                    edge.update_path()
                    logger.info(
                        "collapse: output edge %s port %s missing — connected to node center",
                        getattr(edge, "edge_id", ""),
                        info["port_name"],
                    )
            else:
                new_anchor = comp_item.find_anchor_by_port(info["port_name"], "input")
                if new_anchor:
                    edge._target_anchor = new_anchor
                    edge.end_anchor = new_anchor  # sync public attr
                    edge.update_path()
                else:
                    # Port not found → fallback to node center connection
                    edge._target_anchor = None
                    edge.end_anchor = None  # sync public attr
                    edge.update_path()
                    logger.info(
                        "collapse: input edge %s port %s missing — connected to node center",
                        getattr(edge, "edge_id", ""),
                        info["port_name"],
                    )

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
            src_name = edge.start_node.node_name if hasattr(edge.start_node, "node_name") else ""
            tgt_name = edge.end_node.node_name if hasattr(edge.end_node, "node_name") else ""
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
                edge.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)

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
            src_name = edge.start_node.node_name if hasattr(edge.start_node, "node_name") else ""
            tgt_name = edge.end_node.node_name if hasattr(edge.end_node, "node_name") else ""
            src_in = src_name in node_set
            tgt_in = tgt_name in node_set
            if src_in != tgt_in:  # One inside, one outside
                # Store edge info for restoration
                hidden.append(
                    {
                        "src": src_name,
                        "tgt": tgt_name,
                        "src_port": getattr(edge, "source_port_name", ""),
                        "tgt_port": getattr(edge, "target_port_name", ""),
                    }
                )
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
                src_name = edge.start_node.node_name if hasattr(edge.start_node, "node_name") else ""
                tgt_name = edge.end_node.node_name if hasattr(edge.end_node, "node_name") else ""
                if src_name == info["src"] and tgt_name == info["tgt"]:
                    edge.setVisible(True)
                    edge.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)
                    break
        comp["_hidden_external_edges"] = []

    # ── Edge morphing (expand ↔ collapse) ──

    def _morph_composite_to_internal_edges(self, comp_id: str, comp_item, node_names: list):
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
            port_name = p["port_name"]
            port_to_internal[port_name] = p["internal_node"]
            if port_name == "data":
                port_to_internal["default"] = p["internal_node"]
        for p in comp.get("output_ports", []):
            port_name = p["port_name"]
            port_to_internal[port_name] = p["internal_node"]

        morphed = []

        for edge in list(self._canvas.edges):
            # External node → composite input anchor
            if edge.end_node is comp_item:
                tgt_anchor = getattr(edge, "_target_anchor", None)
                port_name = getattr(tgt_anchor, "port_name", "")
                logger.info(
                    "_morph_composite: edge to composite, port_name=%s, port_to_internal=%s",
                    port_name,
                    port_to_internal,
                )
                internal_name = port_to_internal.get(port_name)
                if internal_name:
                    internal_item = self._canvas.nodes.get(internal_name)
                    if internal_item:
                        edge.setVisible(False)
                        edge.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

                        target_anchor = internal_item.input_anchor
                        if hasattr(internal_item, "anchor_manager"):
                            entry_port = None
                            for p in comp.get("input_ports", []):
                                if p.get("port_name") == port_name or (
                                    port_name == "default" and p.get("port_name") == "data"
                                ):
                                    entry_port = p.get("entry_port")
                                    break
                            if entry_port and entry_port in internal_item.anchor_manager.input_anchors:
                                target_anchor = internal_item.anchor_manager.input_anchors[entry_port]

                        temp = EdgeItem(
                            edge.start_node,
                            internal_item,
                            self._canvas,
                            target_anchor=target_anchor,
                            source_anchor=getattr(edge, "_source_anchor", None),
                        )
                        if hasattr(edge, "_waypoints") and edge._waypoints:
                            temp._waypoints = list(edge._waypoints)
                        self._canvas.scene.addItem(temp)
                        self._canvas.edges.append(temp)
                        temp.update_path()
                        morphed.append({"original": edge, "temp": temp})
                        logger.info(
                            "_morph_composite: created edge from %s to %s, target_anchor=%s",
                            edge.start_node.node_name if hasattr(edge.start_node, "node_name") else "unknown",
                            internal_name,
                            target_anchor,
                        )

            # Composite output anchor → external node
            elif edge.start_node is comp_item:
                src_anchor = getattr(edge, "_source_anchor", None)
                port_name = getattr(src_anchor, "port_name", "")
                internal_name = port_to_internal.get(port_name)
                if internal_name:
                    internal_item = self._canvas.nodes.get(internal_name)
                    if internal_item:
                        edge.setVisible(False)
                        edge.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

                        source_anchor = internal_item.output_anchor
                        if hasattr(internal_item, "anchor_manager"):
                            if port_name in internal_item.anchor_manager.output_anchors:
                                source_anchor = internal_item.anchor_manager.output_anchors[port_name]

                        temp = EdgeItem(
                            internal_item,
                            edge.end_node,
                            self._canvas,
                            target_anchor=getattr(edge, "_target_anchor", None),
                            source_anchor=source_anchor,
                        )
                        if hasattr(edge, "_waypoints") and edge._waypoints:
                            temp._waypoints = list(edge._waypoints)
                        self._canvas.scene.addItem(temp)
                        self._canvas.edges.append(temp)
                        temp.update_path()
                        morphed.append({"original": edge, "temp": temp})

        comp["_morphed_edges"] = morphed

        # ── Sync node_config.json for expanded state ──
        self._sync_configs_for_expand(comp_id, node_names, port_to_internal)
        # 配置快照 — 折叠时用于检测外部修改
        self._snapshot_internal_configs(comp_id, node_names)

    def _morph_internal_to_composite_edges(self, comp_id: str, comp_item, node_names: list):
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
            original.setAcceptedMouseButtons(Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton)
            original.update_path()

        # Morph NEW internal↔external edges to composite↔external edges.
        # Must happen BEFORE _refresh_ports_on_collapse so the saved-edges
        # collector can find and rebind them to correct composite ports.
        # NOTE: edge.start_anchor / edge.end_anchor are separate attrs from
        # edge._source_anchor / edge._target_anchor, and _endpoints() reads
        # the public attrs first. Both must be synced to avoid stale anchor refs.
        for edge in self._canvas.edges:
            src_name = edge.start_node.node_name if hasattr(edge.start_node, "node_name") else ""
            tgt_name = edge.end_node.node_name if hasattr(edge.end_node, "node_name") else ""
            if (src_name in node_set) != (tgt_name in node_set):
                if edge.isVisible():
                    if src_name in node_set:
                        # Internal → external: remap to composite → external
                        edge._desired_source_port_name = f"{src_name}_out"
                        edge.start_node = comp_item
                        edge._source_anchor = None
                        edge.start_anchor = None
                        edge.update_path()
                        logger.info("collapse morph: %s→%s → comp→%s", src_name, tgt_name, tgt_name)
                    else:
                        # External → internal: remap to external → composite
                        old_anchor = getattr(edge, "_target_anchor", None)
                        port_name = getattr(old_anchor, "port_name", "data")
                        edge._desired_target_port_name = port_name
                        edge.end_node = comp_item
                        edge._target_anchor = None
                        edge.end_anchor = None
                        edge.update_path()
                        logger.info("collapse morph: %s→%s → %s→comp", src_name, tgt_name, src_name)

        comp["_morphed_edges"] = []

        # ── Sync node_config.json for collapsed state ──
        conflicts = self._check_config_conflicts(comp_id, node_names)
        if conflicts:
            logger.warning(
                "[%s] 折叠时检测到外部 config 修改: %s",
                comp_id,
                ", ".join(conflicts),
            )
        self._sync_configs_for_collapse(comp_id, node_names)

    # ── Config sync on expand / collapse ──

    def _snapshot_internal_configs(self, comp_id: str, node_names: list):
        """展开时缓存内部节点配置原始内容，折叠时用于检测外部修改。"""
        snap = {}
        for n in node_names:
            cfg_path = Path(get_config_path(str(Path(self._project_path) / "nodes" / n)))
            try:
                snap[n] = cfg_path.read_text(encoding="utf-8")
            except Exception:
                snap[n] = None
        self._composites[comp_id]["_config_snapshot"] = snap

    def _check_config_conflicts(self, comp_id: str, node_names: list) -> list[str]:
        """对比展开快照与当前磁盘内容，返回被外部修改的节点名列表。"""
        snap = self._composites.get(comp_id, {}).get("_config_snapshot", {})
        if not snap:
            return []
        conflicts = []
        for n in node_names:
            cfg_path = Path(get_config_path(str(Path(self._project_path) / "nodes" / n)))
            try:
                current = cfg_path.read_text(encoding="utf-8")
            except Exception:
                current = None
            if snap.get(n) is not None and current != snap[n]:
                conflicts.append(n)
        return conflicts

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
        nodes_dir = Path(self._project_path) / "nodes"
        if not self._canvas:
            return

        # Build map: internal_name → external_infos
        in_conns: dict[str, list] = {}  # internal_name → [{source_name, source_path, port_name}]
        out_conns: dict[str, list] = {}  # internal_name → [{target_name, target_port, port_name}]

        for edge in self._canvas.edges:
            if not edge.isVisible():
                continue
            src = edge.start_node
            tgt = edge.end_node
            if src is None or tgt is None:
                continue
            src_name = src.node_name if hasattr(src, "node_name") else ""
            tgt_name = tgt.node_name if hasattr(tgt, "node_name") else ""
            if not src_name or not tgt_name:
                continue

            # External → internal (input direction)
            if src_name not in node_set and tgt_name in node_set:
                port_name = getattr(getattr(edge, "_target_anchor", None), "port_name", "") or "default"
                src_path = str((nodes_dir / src_name / "output.json").resolve())
                in_conns.setdefault(tgt_name, []).append(
                    {
                        "source_name": src_name,
                        "source_path": src_path,
                        "port_name": port_name,
                    }
                )

            # Internal → external (output direction)
            if src_name in node_set and tgt_name not in node_set:
                port_name = getattr(getattr(edge, "_source_anchor", None), "port_name", "") or "default"
                tgt_port = getattr(getattr(edge, "_target_anchor", None), "port_name", "") or "default"
                out_conns.setdefault(src_name, []).append(
                    {
                        "target_name": tgt_name,
                        "target_port": tgt_port,
                        "port_name": port_name,
                    }
                )

        # ── Phase 2: also read from _port_routing ──
        routing = self._get_port_routing(comp_id)
        for port_name, route in routing.get("input", {}).items():
            internal_name = port_to_internal.get(port_name)
            if internal_name and internal_name in node_set:
                src_path = route.get("source_output_path", "")
                if src_path:
                    in_conns.setdefault(internal_name, []).append(
                        {
                            "source_name": self._extract_node_from_path(src_path) or "external",
                            "source_path": src_path,
                            "port_name": port_name,
                        }
                    )
        for port_name, route in routing.get("output", {}).items():
            internal_name = port_to_internal.get(port_name)
            if internal_name and internal_name in node_set:
                tgt_node = route.get("target_node", "")
                tgt_port = route.get("target_port", "default")
                if tgt_node:
                    out_conns.setdefault(internal_name, []).append(
                        {
                            "target_name": tgt_node,
                            "target_port": tgt_port,
                            "port_name": port_name,
                        }
                    )

        # Apply input connections
        for internal_name, entries in in_conns.items():
            config_path = Path(get_config_path(str(nodes_dir / internal_name)))
            try:
                with config_path.open(encoding="utf-8") as f:
                    cfg = _json.load(f)
            except Exception:
                cfg = {}
            cfg["listen_upper_file"] = entries[0]["source_path"]
            try:
                with config_path.open("w", encoding="utf-8") as f:
                    _json.dump(cfg, f, indent=2, ensure_ascii=False)
                logger.info("expand sync: %s listen_upper_file → %s", internal_name, entries[0]["source_path"])
            except Exception as e:
                logger.error("expand sync %s: %s", internal_name, e)

        # Apply output connections
        for internal_name, entries in out_conns.items():
            config_path = Path(get_config_path(str(nodes_dir / internal_name)))
            try:
                with config_path.open(encoding="utf-8") as f:
                    cfg = _json.load(f)
            except Exception:
                cfg = {}
            cfg.setdefault("out_connections", {})
            for entry in entries:
                cfg["out_connections"][entry["port_name"]] = f"{entry['target_name']}|{entry['target_port']}"
            try:
                with config_path.open("w", encoding="utf-8") as f:
                    _json.dump(cfg, f, indent=2, ensure_ascii=False)
                logger.info(
                    "expand sync: %s out_connections updated: %s", internal_name, list(cfg["out_connections"].keys())
                )
            except Exception as e:
                logger.error("expand sync %s: %s", internal_name, e)

    def _find_entry_for_collapse(self, node_names: list, comp: dict) -> str:
        """找出复合节点内 DAG 的入口节点（无内部上游的节点）。"""
        edges = comp.get("_internal_edges", [])
        targets = {e.get("tgt", e.get("to", "")) for e in edges}
        for n in node_names:
            if n not in targets:
                return n
        return node_names[0] if node_names else ""

    def _find_entry_node(self, comp_id: str) -> str:
        """通过 comp_id 找出 DAG 入口节点（供外部连线时使用）。"""
        comp = self._composites.get(comp_id, {})
        node_names = comp.get("nodes", [])
        return self._find_entry_for_collapse(node_names, comp)

    def _find_exit_node(self, comp_id: str) -> str:
        """通过 comp_id 找出 DAG 出口节点（无内部下游的节点）。"""
        comp = self._composites.get(comp_id, {})
        edges = comp.get("_internal_edges", [])
        sources = {e.get("src", e.get("from", "")) for e in edges}
        node_names = comp.get("nodes", [])
        for n in node_names:
            if n not in sources:
                return n
        return node_names[-1] if node_names else ""

    def _sync_configs_for_collapse(self, comp_id: str, node_names: list):
        """On collapse: sync external refs back to _port_routing, then clear internal configs.

        Phase 1: Read external connections from internal node configs → write to _port_routing
        Phase 2: Clear listen_upper_file / out_connections pointing outside the composite
        """
        import json as _json

        node_set = set(node_names)
        nodes_dir = Path(self._project_path) / "nodes"

        # Build reverse mapping: internal_node → (port_name, port_type)
        comp = self._composites.get(comp_id, {})
        internal_to_input_port = {}
        internal_to_output_port = {}
        for p in comp.get("input_ports", []):
            internal_to_input_port[p.get("internal_node", "")] = p.get("port_name", "")
        for p in comp.get("output_ports", []):
            internal_to_output_port[p.get("internal_node", "")] = p.get("port_name", "")

        # ── Phase 1: sync external refs back to _port_routing ──
        # 找出入口节点：DAG 中没有内部上游的节点
        entry_node = self._find_entry_for_collapse(node_names, comp)

        for node_name in node_names:
            config_path = Path(get_config_path(str(nodes_dir / node_name)))
            try:
                with config_path.open(encoding="utf-8") as f:
                    cfg = _json.load(f)
            except Exception:
                continue

            # Input direction: listen_upper_file pointing externally
            listen = cfg.get("listen_upper_file", "")
            if listen:
                upstream = self._extract_node_from_path(listen)
                if upstream and upstream not in node_set:
                    port_name = internal_to_input_port.get(node_name, "")
                    if not port_name and entry_node:
                        # 下游节点有外部监听但无端口映射 → 路由到入口节点的第一个端口
                        port_name = internal_to_input_port.get(entry_node, "")
                    if port_name:
                        self.set_input_routing(comp_id, port_name, listen)
                        logger.info(
                            "collapse sync: _port_routing input[%s] ← %s (from %s)", port_name, listen, node_name
                        )

            # Input direction (sub-ports): port_mappings pointing externally
            port_mappings = cfg.get("port_mappings", {})
            if isinstance(port_mappings, dict):
                for pm_port, pm_path in port_mappings.items():
                    if not isinstance(pm_path, str) or not pm_path:
                        continue
                    pm_upstream = self._extract_node_from_path(pm_path)
                    if pm_upstream and pm_upstream not in node_set:
                        self.set_input_routing(comp_id, pm_port, pm_path)
                        logger.info(
                            "collapse sync: _port_routing input[%s] ← %s (port_mappings from %s)",
                            pm_port,
                            pm_path,
                            node_name,
                        )

            # Output direction: out_connections pointing externally
            out_conns = cfg.get("out_connections", {})
            for _port_key, target in out_conns.items():
                if isinstance(target, str) and target:
                    ext_node = target.split("|")[0]
                    if ext_node and ext_node not in node_set:
                        tgt_port = target.split("|")[1] if "|" in target else "default"
                        port_name = internal_to_output_port.get(node_name, "")
                        if not port_name:
                            # 非叶子节点有外部连接 → 动态生成端口名（与 _identify_ports 一致）
                            port_name = f"{node_name}_out"
                            internal_to_output_port[node_name] = port_name
                        self.set_output_routing(comp_id, port_name, None, ext_node, tgt_port)
                        logger.info(
                            "collapse sync: _port_routing output[%s] → %s|%s (from %s)",
                            port_name,
                            ext_node,
                            tgt_port,
                            node_name,
                        )

        # ── Phase 2: clear external refs from internal configs ──
        for node_name in node_names:
            config_path = Path(get_config_path(str(nodes_dir / node_name)))
            try:
                with config_path.open(encoding="utf-8") as f:
                    cfg = _json.load(f)
            except Exception:
                continue

            changed = False

            # Clear listen_upper_file if it points externally
            listen = cfg.get("listen_upper_file", "")
            if listen:
                upstream = self._extract_node_from_path(listen)
                if upstream and upstream not in node_set:
                    cfg["listen_upper_file"] = ""
                    changed = True
                    logger.info("collapse sync: %s listen_upper_file cleared (was → %s)", node_name, upstream)

            # Remove port_mappings entries pointing externally
            pmappings = cfg.get("port_mappings", {})
            pm_to_remove = []
            if isinstance(pmappings, dict):
                for pm_port, pm_path in pmappings.items():
                    if isinstance(pm_path, str):
                        pm_upstream = self._extract_node_from_path(pm_path)
                        if pm_upstream and pm_upstream not in node_set:
                            pm_to_remove.append(pm_port)
                for pm_port in pm_to_remove:
                    del pmappings[pm_port]
                    changed = True
                    logger.info("collapse sync: %s port_mappings[%s] removed (was → external)", node_name, pm_port)

            # Remove out_connections entries pointing externally
            out_conns = cfg.get("out_connections", {})
            to_remove = []
            for port_key, target in list(out_conns.items()):
                ext_node = target.split("|")[0] if isinstance(target, str) else ""
                if ext_node and ext_node not in node_set:
                    to_remove.append(port_key)
            for port_key in to_remove:
                del out_conns[port_key]
                changed = True
                logger.info("collapse sync: %s out_connections[%s] removed (was → external)", node_name, port_key)

            if changed:
                try:
                    with config_path.open("w", encoding="utf-8") as f:
                        _json.dump(cfg, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    logger.error("collapse sync %s: %s", node_name, e)

    @staticmethod
    def _extract_node_from_path(file_path: str) -> str | None:
        """Extract a node name from a file path like .../nodes/<name>/output.json."""
        if not file_path:
            return None
        import re

        normalized = file_path.replace("\\", "/")
        m = re.search(r"/nodes/([^/]+)", normalized)
        if m:
            return m.group(1)
        m = re.search(r"\.\./([^/]+)/output\.json", normalized)
        if m:
            return m.group(1)
        return None

    def _resolve_node_logical_name(self, name_or_dir: str | None, nodes_data: dict) -> str:
        """把物理目录名（如 python_node_demo_1）反查为 nodes_data 逻辑名（如 node_python_demo_1）。
        若 name_or_dir 已经是逻辑名则原样返回。若无法匹配则返回原值但打 WARNING。"""
        if not name_or_dir:
            return ""
        # 已经在 nodes_data 中 → 直接返回
        if name_or_dir in nodes_data:
            return name_or_dir
        target_path_str: str | None = None
        has_sep = ("/" in name_or_dir) or ("\\" in name_or_dir)
        if not has_sep:
            # name_or_dir 是纯目录名，构造 <project>/nodes/<name_or_dir> 作为 path 反查
            candidate = Path(self._project_path) / "nodes" / name_or_dir
            try:
                target_path_str = str(candidate.resolve())
            except Exception:
                target_path_str = str(candidate)
        else:
            # 本身是路径：取到 <path>/nodes/<x>/output.json 里的 <nodes>/<x> 段的目录即可
            try:
                p = Path(name_or_dir)
                if p.name.endswith(".json"):
                    p = p.parent  # 去 output.json 得到节点目录
                target_path_str = str(p.resolve())
            except Exception:
                target_path_str = str(p)
        if target_path_str:
            # nodes_data path 反查（与 canonical_edge_resolver 一致）
            for logical_key, meta in nodes_data.items():
                p_meta = meta.get("path") or ""
                if not p_meta:
                    continue
                try:
                    mp = str(Path(p_meta).resolve())
                except Exception:
                    mp = str(Path(p_meta))
                if mp == target_path_str:
                    return logical_key
                # 宽松匹配：目录名部分相等
                try:
                    if Path(mp).name == Path(target_path_str).name:
                        return logical_key
                except Exception:
                    pass
            logger.warning(
                "[IDENTITY-MISMATCH-MORPH] '%s' 无法在 nodes_data 反查到逻辑名"
                "（canvas.nodes 索引会找不到 → PhaseC create_edge 失败！）— fallback to original",
                name_or_dir,
            )
        return name_or_dir

    # ── 核心操作 ──

    def compress(self, node_names: list, name: str = "") -> tuple[bool, str, str | None]:
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
                status = node_data.get("status", "")
                if status in ("running", "idle", "starting", "stopping"):
                    return False, t(TK._COMPOSITE_RUNNING).format(name=n, status=status), None

        # Language compatibility check
        node_paths_map = {}
        for n in node_names:
            node_data = self._canvas.parent_window.nodes_data.get(n, {}) if self._canvas.parent_window else {}
            node_path = node_data.get("path", "")
            if not node_path:
                node_path = str(Path(self._project_path) / "nodes" / n)
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
            src = edge_item.start_node.node_name if hasattr(edge_item.start_node, "node_name") else ""
            tgt = edge_item.end_node.node_name if hasattr(edge_item.end_node, "node_name") else ""
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

        for n in original_positions:
            original_positions[n]["x"] -= cx
            original_positions[n]["y"] -= cy

        ports = self._identify_ports(node_names, edges_list, nodes_data)

        # ── 防错：单入口 DAG 校验 ──
        is_valid, err_msg = self._validate_dag_single_entry(node_names, edges_list, nodes_data)
        if not is_valid:
            return False, err_msg, None

        # ── 提取入口节点过滤规则 ──
        input_filter_rules = self._extract_entry_filter_rules(node_names, edges_list, nodes_data)

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
            "edges_list": edges_list,
            "input_filter_rules": input_filter_rules,
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
            themed_message(None, t("k_title_error"), f"Failed to set up composite environment:\n{msg}", "error")
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
        input_filter_rules = data.get("input_filter_rules")

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
            "input_filter_rules": input_filter_rules,
        }
        # 创建生命周期状态机（初始状态: CREATED）
        self._get_lifecycle(comp_id)
        self.save()

        # 创建 composite_nodes/<comp_id>/ 完整目录结构
        edges_list = data.get("edges_list", [])
        self._create_comp_config_dir(
            comp_id,
            node_names,
            edges_list,
            ports,
            display_name,
            common_lang,
            cx,
            cy,
            original_positions,
            input_filter_rules,
        )

        # 同步 pipeline.json（从 composite.json 提取 DAG）
        self._sync_pipeline(comp_id)

        # Canvas
        self._canvas_compress(comp_id, node_names, cx, cy, display_name, ports)

        # ── Phase3 灰度：并行调用每个子节点 compress_into_composite（差异告警，不影响主流程）
        self._gray_compress(comp_id)
        # ──

    def decompress(self, comp_id: str) -> tuple[bool, str]:
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

        # ── 状态机：进入移除流程 ──
        lc = self._get_lifecycle(comp_id)
        lc.handle("decompress")

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
            except (RuntimeError, ValueError, KeyError):
                pass
            try:
                self._group_manager.delete_group(group_name)
            except (RuntimeError, ValueError, KeyError):
                pass

        # 清除
        del self._composites[comp_id]
        self.save()

        # 清理 orchestrator 和复合节点 venv
        orch_path = Path(self._project_path) / f"orchestrator_{comp_id}.py"
        try:
            orch_path.unlink()
        except OSError:
            pass

        remove_comp_env(self._project_path, comp_id, logger)

        # 清理 composite_nodes/<comp_id>/ (日志存档后删除)
        self._decompress_cleanup(comp_id)

        # ── 状态机：标记已删除 ──
        lc.handle("remove_done")
        self._lifecycle.pop(comp_id, None)

        # ── Phase3 灰度：并行调用每个子节点 decompress_from_composite（差异告警，不影响主流程）
        self._gray_decompress(comp_id, list(node_names))
        # ──

        return True, t(TK._COMPOSITE_DECOMPRESSED).format(n=len(node_names))

    def set_runtime(self, comp_id: str, mode: str) -> tuple[bool, str]:
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

    def get_runtime(self, comp_id: str) -> str | None:
        c = self._composites.get(comp_id)
        return c.get("runtime") if c else None

    def get_nodes(self, comp_id: str) -> list[str]:
        c = self._composites.get(comp_id)
        return list(c["nodes"]) if c else []

    def get_all_composites(self) -> dict[str, dict]:
        return dict(self._composites)

    def get_node_count(self, comp_id: str) -> int:
        return len(self.get_nodes(comp_id))

    # ── DAG ──

    def get_dag(self, comp_id: str) -> list[dict]:
        """推导复合节点内部的 DAG（原画布连线）。"""
        node_set = set(self.get_nodes(comp_id))
        if not self._canvas:
            return []
        edges_list = []
        for edge_item in self._canvas.edges:
            src = edge_item.start_node.node_name if hasattr(edge_item.start_node, "node_name") else ""
            tgt = edge_item.end_node.node_name if hasattr(edge_item.end_node, "node_name") else ""
            if src in node_set and tgt in node_set:
                edges_list.append(
                    {
                        "from": src,
                        "to": tgt,
                        "source_port": getattr(edge_item, "source_port_name", "") or "",
                        "target_port": getattr(edge_item, "target_port_name", "") or "",
                    }
                )
        return edges_list

    def _topo_sort_nodes(self, comp_id: str) -> list[str]:
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

    def _has_cycle(self, node_set: set, edges_list: list[dict]) -> list:
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
            src = edge_item.start_node.node_name if hasattr(edge_item.start_node, "node_name") else ""
            tgt = edge_item.end_node.node_name if hasattr(edge_item.end_node, "node_name") else ""
            src_in = src in node_set
            tgt_in = tgt in node_set

            if src_in and not tgt_in:
                outputs.append(
                    {
                        "name": f"{src}_to_{tgt}",
                        "internal_node": src,
                        "external_node": tgt,
                        "port": getattr(edge_item, "source_port_name", "") or "output",
                    }
                )
            elif not src_in and tgt_in:
                inputs.append(
                    {
                        "name": f"{src}_to_{tgt}",
                        "external_node": src,
                        "internal_node": tgt,
                        "port": getattr(edge_item, "target_port_name", "") or "input",
                    }
                )

        return {"inputs": inputs, "outputs": outputs}

    # ── Orchestrator 生成与启动 ──

    def generate_orchestrator(self, comp_id: str) -> str:
        """生成 orchestrator.py 到 composite_nodes/<comp_id>/ 并返回路径。

        orchestrator.py 是通用编排引擎（从 pipeline.json 读取 DAG），
        采用 while True 常驻轮询模式。首次生成后 DAG 变更仅需更新
        pipeline.json 并写入 .pipe 信号文件，编排器会自动热加载。
        """
        comp_dir = self._comp_config_dir(self._project_path, comp_id)
        comp_dir.mkdir(parents=True, exist_ok=True)

        # 1. 同步 pipeline.json（从 composite.json 提取 DAG）
        self._sync_pipeline(comp_id)

        # 2. 生成 orchestrator.py
        code = render_orchestrator_script(comp_id=comp_id)
        orch_path = comp_dir / "orchestrator.py"
        try:
            with orch_path.open("w", encoding="utf-8") as f:
                f.write(code)
        except (PermissionError, OSError) as e:
            logger.error("生成 orchestrator 失败: %s", e)
            raise RuntimeError(t(TK._COMPOSITE_WRITE_ORCH_FAILED).format(path=str(orch_path), err=str(e))) from e

        self._composites[comp_id]["orchestrator_path"] = str(orch_path)
        self.save()
        return str(orch_path)

    def start_inprocess(self, comp_id: str) -> tuple[bool, str]:
        """启动 inprocess 模式复合节点。"""
        lc = self._get_lifecycle(comp_id)

        # ── 状态机守卫：防止 TOCTOU 重复启动 ──
        if not lc.is_restartable:
            return False, t(TK.COMPOSITE_ALREADY_RUNNING) if lc.is_active else t("k_err_unknown")
        lc.handle("start")

        orch_path = self.generate_orchestrator(comp_id)
        virtual_name = f"__composite_{comp_id}"

        # ── 双重安全检查：_active_processes 是最终防线（状态机 + dict 双重保险）──
        if virtual_name in self._active_processes:
            proc = self._active_processes[virtual_name]
            if proc.poll() is None:
                lc.handle("start_fail")  # 回退状态
                return False, t(TK.COMPOSITE_ALREADY_RUNNING)

        # ── Python 解释器 ──
        project_root = self._project_path
        comp_dir = self._comp_venv_dir(comp_id)
        python_exe = get_python_exe(comp_dir) or ""

        if not python_exe or not Path(python_exe).exists():
            if os.name == "nt":
                python_exe = str(Path(project_root) / "venv" / "Scripts" / "python.exe")
            else:
                python_exe = str(Path(project_root) / "venv" / "bin" / "python3")
        if not Path(python_exe).exists():
            python_exe = sys.executable

        # ── 日志文件 ──
        log_dir = self._comp_logs_dir(self._project_path, comp_id)
        log_dir.mkdir(parents=True, exist_ok=True)
        _out_f = None
        _err_f = None
        try:
            _out_f = open(log_dir / "composite_output.log", "w", encoding="utf-8")
            _err_f = open(log_dir / "composite_error.log", "w", encoding="utf-8")
        except (PermissionError, OSError) as e:
            logger.error("[%s] 无法打开日志文件: %s", comp_id, e)
            lc.handle("start_fail")
            return False, t(TK._COMPOSITE_LOG_OPEN_FAILED).format(err=str(e))

        proc = None
        try:
            proc = subprocess.Popen(
                [python_exe, orch_path],
                cwd=project_root,
                stdout=_out_f,
                stderr=_err_f,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
            )
            self._active_processes[virtual_name] = proc
            self._composite_log_files[comp_id] = (_out_f, _err_f)
            logger.info("[%s] 复合节点已启动 PID=%d", comp_id, proc.pid)

            # ── 启动后健康检查 ──
            import time

            time.sleep(0.3)
            ret = proc.poll()
            if ret is not None and ret != 0:
                stderr_output = ""
                try:
                    _err_f.flush()
                    stderr_output = (log_dir / "composite_error.log").read_text(encoding="utf-8", errors="replace")
                except OSError:
                    pass
                self._active_processes.pop(virtual_name, None)
                self._composite_log_files.pop(comp_id, (None, None))
                _out_f.close()
                _err_f.close()
                lc.handle("start_timeout")
                return False, t(TK._COMPOSITE_CRASH).format(code=ret) + f"\n{stderr_output[:500]}"

            # ── PID 文件 ──
            pid_file = Path(project_root) / f"__composite_{comp_id}.pid"
            with pid_file.open("w") as f:
                f.write(str(proc.pid))

            lc.handle("start_ok")
            if ret == 0:
                return True, t(TK._COMPOSITE_FINISHED)
            return True, t(TK._COMPOSITE_STARTED).format(pid=proc.pid)
        except Exception as e:
            # ── 异常路径：完整清理（修复之前的资源泄漏）──
            lc.handle("start_fail")
            if proc is not None and proc.poll() is None:
                try:
                    proc.kill()
                    proc.wait(timeout=5)
                except (ProcessLookupError, OSError):
                    pass
            self._active_processes.pop(virtual_name, None)
            # 清理日志文件句柄
            log_files = self._composite_log_files.pop(comp_id, (None, None))
            for fh in log_files:
                if fh is not None:
                    try:
                        fh.close()
                    except OSError:
                        pass
            logger.error("[%s] 启动失败: %s", comp_id, e)
            return False, str(e)

    def start_process_mode(self, comp_id: str) -> tuple[bool, str]:
        """启动 process 模式复合节点（各节点独立启动）。"""
        from ui.core.node.node_control_service import node_control_service

        node_names = self.get_nodes(comp_id)
        for n in node_names:
            node_control_service.start_node(n)
        return True, t(TK._COMPOSITE_STARTED_N).format(n=len(node_names))

    def stop_composite(self, comp_id: str) -> tuple[bool, str]:
        """停止复合节点。

        先尝试通过内存中的 Popen 对象终止；若已丢失（如 _composite_manager
        被重建导致 _active_processes 为空），则从 PID 文件读取 PID 后强制 kill。
        Windows 上使用 taskkill /F /T 确保完整终止进程树。
        """
        lc = self._get_lifecycle(comp_id)

        # ── 状态机守卫：只在活跃状态时允许停止 ──
        if not lc.is_active:
            return False, t("k_err_not_running")
        lc.handle("stop")

        virtual_name = f"__composite_{comp_id}"
        proc = self._active_processes.get(virtual_name)
        killed = False

        # ── 路径 1: 内存中的 Popen 对象可用 ──
        if proc is not None:
            if proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    try:
                        proc.kill()
                        proc.wait(timeout=5)
                    except (ProcessLookupError, OSError):
                        pass
            del self._active_processes[virtual_name]
            killed = True
            logger.info("[%s] 复合节点已停止 (via Popen)", comp_id)

        # ── 路径 2: 兜底 — 从 PID 文件读取 PID 并强制终止 ──
        pid_paths = [
            Path(self._project_path) / f"__composite_{comp_id}.pid",
            self._comp_config_dir(self._project_path, comp_id) / ".pid",
        ]
        for pid_file in pid_paths:
            try:
                if not pid_file.exists():
                    continue
                pid = int(pid_file.read_text().strip())
            except (OSError, ValueError):
                continue
            if self._kill_pid_force(pid):
                killed = True
                logger.info("[%s] 复合节点已停止 (via PID file, pid=%d)", comp_id, pid)

        # 关闭日志文件句柄
        log_files = self._composite_log_files.pop(comp_id, (None, None))
        for fh in log_files:
            if fh is not None:
                try:
                    fh.close()
                except OSError:
                    pass

        # 清理 PID 文件
        for pid_file in pid_paths:
            try:
                pid_file.unlink(missing_ok=True)
            except OSError:
                pass

        # ── 状态机：根据结果设置终态 ──
        if killed:
            lc.handle("stop_ok")
        else:
            lc.handle("stop_fail")

        if killed:
            msg = t(TK.COMPOSITE_STOPPED)
        else:
            msg = t(TK.COMPOSITE_STOP_FAILED)
        return killed, msg

    @staticmethod
    def _kill_pid_force(pid: int) -> bool:
        """跨平台强制终止进程。返回 True 表示成功终止。"""
        try:
            import psutil
        except ImportError:
            psutil = None
        killed = False
        if os.name == "nt":
            # Windows: taskkill /F /T 杀死进程树
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    timeout=10,
                )
                killed = True
            except (subprocess.TimeoutExpired, OSError) as exc:
                logger.warning("taskkill failed for pid=%d: %s", pid, exc)
        else:
            # Unix: SIGKILL 进程树
            try:
                parent = psutil.Process(pid) if psutil else None
                if parent:
                    children = parent.children(recursive=True)
                    for child in children:
                        child.kill()
                    _, alive = psutil.wait_procs(children + [parent], timeout=5)
                    for p in alive:
                        p.kill()
                    killed = True
                else:
                    os.kill(pid, 9)
                    killed = True
            except (ProcessLookupError, PermissionError, OSError) as exc:
                logger.warning("kill failed for pid=%d: %s", pid, exc)
        return killed

    def execute(self, comp_id: str) -> bool:
        """统一执行入口，根据 comp 配置的 transport 字段路由到本地或远程。"""
        comp = self._composites.get(comp_id)
        if not comp:
            logger.error("execute: 复合节点 %s 不存在", comp_id)
            return False

        transport = comp.get("transport", "local")
        if transport == "local":
            # 启动守卫: 检查子节点是否独立运行中
            allowed, msg, conflicts = self.check_composite_start(comp_id)
            if not allowed:
                themed_message(None, t("k_title_warning"), msg, "warning")
                return False
            return self._execute_local(comp_id)
        else:
            from ui.core.system.transports import get_transport_handler

            handler = get_transport_handler(transport)
            return handler.execute(comp_id, comp)

    def _execute_local(self, comp_id: str) -> bool:
        """当前逻辑：决定 inprocess vs process 模式并启动。"""
        runtime = self.get_runtime(comp_id) or "inprocess"
        if runtime == "inprocess":
            ok, msg = self.start_inprocess(comp_id)
        else:
            ok, msg = self.start_process_mode(comp_id)
        if not ok:
            logger.error("_execute_local %s: %s", comp_id, msg)
        return ok

    @staticmethod
    def composite_log_paths(comp_dir: str | Path) -> list[Path]:
        """返回复合节点的日志文件列表。优先查找 composite_nodes/<id>/logs/。"""
        p = Path(comp_dir)
        # 尝试 composite_nodes/<comp_id>/logs/ 路径
        if p.name != "logs":
            logs_from_comp_nodes = p / COMPOSITE_NODES_DIR
            if logs_from_comp_nodes.exists():
                candidate = logs_from_comp_nodes / "logs"
                if candidate.exists():
                    p = candidate
            else:
                p = p / "logs"
        out_log = p / "composite_output.log"
        err_log = p / "composite_error.log"
        return [f for f in (out_log, err_log) if f.exists()]

    def _get_lifecycle(self, comp_id: str) -> CompositeLifecycleSM:
        """获取或创建复合节点生命周期状态机。"""
        if comp_id not in self._lifecycle:
            self._lifecycle[comp_id] = CompositeLifecycleSM(comp_id)
        return self._lifecycle[comp_id]

    def is_running(self, comp_id: str) -> bool:
        """检查复合节点是否在运行（委托生命周期状态机）。"""
        lc = self._lifecycle.get(comp_id)
        if lc is not None:
            return lc.is_active
        # 兜底：状态机尚未初始化时，回退到原来的检查方式
        virtual_name = f"__composite_{comp_id}"
        proc = self._active_processes.get(virtual_name)
        return proc is not None and proc.poll() is None

    def get_health(self, comp_id: str) -> dict | None:
        """读取复合节点编排器写入的 status.json，返回子节点健康状态。

        Returns:
            None   — status.json 不存在（尚未执行过 DAG）
            dict   — {"comp_id": str, "updated_at": str, "last_run_id": str,
                      "nodes": {name: {"status": "ok"|"fail"|"pending", ...}}}
        """
        status_path = self._comp_config_dir(self._project_path, comp_id) / "status.json"
        if not status_path.exists():
            return None
        try:
            import json as _json

            return _json.loads(status_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("[%s] 读取 status.json 失败: %s", comp_id, e)
            return None

    def rename(self, comp_id: str, new_name: str):
        """重命名复合节点的展示名称（仅改动 display_name 字段，不影响 comp_id 或 venv）。
        若 new_name 为空，清除 display_name（回退到 hex ID 显示）。"""
        comp = self._composites.get(comp_id)
        if not comp:
            raise ValueError(f"Composite not found: {comp_id}")
        comp["display_name"] = new_name.strip() if new_name and new_name.strip() else ""
        self.save()

    # ── 辅助 ──

    def _find_composite_of_node(self, node_name: str) -> str | None:
        for cid, c in self._composites.items():
            if node_name in c.get("nodes", []):
                return cid
        return None

    # ── 启动守卫 ──

    def check_subnode_start(self, node_name: str) -> tuple[bool, str, str | None]:
        """启动独立节点前检查：是否属于运行中的复合节点。

        Returns:
            (allowed, message, owner_comp_id | None)
            - allowed=True: 可以启动
            - allowed=False: 被运行中的复合节点阻止
        """
        owner = self._find_composite_of_node(node_name)
        if not owner:
            return True, "", None

        if self.is_running(owner):
            comp = self._composites.get(owner, {})
            comp_display = comp.get("display_name") or owner
            return False, t(TK._START_SUBNODE_CONFLICT).format(node=node_name, composite=comp_display), owner
        return True, "", owner

    def check_composite_start(self, comp_id: str) -> tuple[bool, str, list[tuple[str, int]]]:
        """启动复合节点前检查：子节点是否独立运行中。

        Returns:
            (allowed, message, conflicts)
            - allowed=True: 可以启动
            - allowed=False: 有子节点独立运行中
            - conflicts: [(node_name, pid), ...]
        """
        try:
            import psutil
        except ImportError:
            psutil = None

        node_names = self.get_nodes(comp_id)
        conflicts = []

        for n in node_names:
            # 检查 PID 文件
            pid_file = Path(self._project_path) / "nodes" / n / ".pid"
            if pid_file.exists():
                try:
                    pid = int(pid_file.read_text().strip())
                    if psutil and psutil.pid_exists(pid):
                        conflicts.append((n, pid))
                except (OSError, ValueError):
                    pass

        if conflicts:
            details = "\n".join(f"  - {n} (PID={p})" for n, p in conflicts)
            comp = self._composites.get(comp_id, {})
            comp_display = comp.get("display_name") or comp_id
            return False, t(TK._START_COMPOSITE_CONFLICT).format(composite=comp_display, details=details), conflicts

        return True, "", []

    def stop_conflicting_subnodes(self, conflicts: list[tuple[str, int]]):
        """停止与复合节点冲突的独立运行子节点。"""
        try:
            import psutil
        except ImportError:
            logger.warning("psutil 不可用，无法停止冲突子节点")
            return

        for name, pid in conflicts:
            try:
                proc = psutil.Process(pid)
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    proc.kill()
                logger.info("启动守卫: 已停止独立进程 %s (PID=%d)", name, pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied, ProcessLookupError, OSError):
                logger.info("启动守卫: 进程 %s (PID=%d) 已不存在", name, pid)
            # 清理 PID 文件
            pid_file = Path(self._project_path) / "nodes" / name / ".pid"
            try:
                pid_file.unlink()
            except OSError:
                pass

    def _find_internal_by_port(self, comp_id: str, port_name: str, port_type: str = "output") -> str | None:
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

    # =========================================================================
    # Phase4.1 Morph 新机制 —— 阶段A 只读收集 + 端口复用 + 互斥断言
    # =========================================================================

    def _nodes_data_global(self) -> dict:
        """统一拿 nodes_data 全局注册表（parent_window.nodes_data 兜底空 dict）。"""
        if self._canvas and getattr(self._canvas, "parent_window", None):
            return getattr(self._canvas.parent_window, "nodes_data", {}) or {}
        return {}

    def collect_expand_morph_list(self, comp_id: str) -> list[dict]:
        """expand 阶段A：在 comp 配置/UI 边/EdgeKey 全部完好未动时机，
        全量抄一份 morph 计划到内存。后续阶段B清配置不会丢此信息。

        优先从磁盘 composite.json.external_connections 读真相（避免内存 _port_routing
        因 debounce / 异常重启 为空），回写 merge 到内存后再做收集。
        返回 list[dict]，每个 dict 字段符合顶部 MORPH 条目结构。
        STALE 路由（上游不在 nodes_data / target_node 空）跳过 morph，并打日志。
        """
        morph_list: list[dict] = []
        nodes_data = self._nodes_data_global()
        comp = self._composites.get(comp_id, {})

        # ================================================================
        # —— Step 0：先从 composite.json 磁盘回读 external_connections 回写 merge 到内存 ——
        #        （解决 debounce 300ms 窗口内被清空、或各种中间态把内存 _port_routing 清空的问题）
        # ================================================================
        disk_cfg = self._load_composite_config(comp_id)
        disk_ext = disk_cfg.get("external_connections", {}) if isinstance(disk_cfg, dict) else {}
        if disk_ext and isinstance(disk_ext, dict):
            disk_in = disk_ext.get("input", {}) or {}
            disk_out = disk_ext.get("output", {}) or {}
            if disk_in or disk_out:
                self._ensure_port_routing(comp_id)
                mem_routing = self._composites[comp_id]["_port_routing"]
                merged_in = 0
                for k, v in disk_in.items():
                    if k not in mem_routing["input"] or not mem_routing["input"].get(k):
                        mem_routing["input"][k] = v if isinstance(v, dict) else {"source_output_path": v}
                        merged_in += 1
                merged_out = 0
                for k, v in disk_out.items():
                    if k not in mem_routing["output"] or not mem_routing["output"].get(k):
                        mem_routing["output"][k] = v if isinstance(v, dict) else {}
                        merged_out += 1
                if merged_in or merged_out:
                    logger.info(
                        "[MORPH-MERGE-DISK] expand comp=%s merged_from_disk: input=%d output=%d",
                        comp_id,
                        merged_in,
                        merged_out,
                    )

        # ================================================================
        # —— Step 0.5：Canvas Edge Truth Back-Probe（配置 vs 画布边反向校验）——
        # 当处于折叠态（comp_item 可见且没展开）时，配置里声明的每条 external_connections
        # 必须有对应画布上可见的 external↔comp_item 边与之对应。否则：
        #   → 用户明确删除了该边，但 composite.json 因 debounce/异常没及时清
        #   → 此时不得当作"真路由"塞进 morph_list，否则展开后会自动连上已断开的连接
        # ================================================================
        comp_item = self._canvas.nodes.get(comp_id) if self._canvas else None
        frame_exists = f"__frame__{comp_id}" in self._canvas.nodes if self._canvas else False
        folded_visible = comp_item is not None and getattr(comp_item, "isVisible", lambda: True)() and not frame_exists
        stale_in_ports_purged: list[str] = []
        stale_out_ports_purged: list[str] = []
        if folded_visible and self._canvas and hasattr(self._canvas, "edges"):
            # 先收集画布上 comp_item 作为端点的所有可见边
            real_inputs: set[tuple[str, str, str]] = set()  # {(upstream_logical_name, upstream_out_port, comp_in_port)}
            real_outputs: set[tuple[str, str, str]] = (
                set()
            )  # {(comp_out_port, downstream_logical_name, downstream_in_port)}
            for edge in list(self._canvas.edges):
                if not getattr(edge, "isVisible", lambda: True)():
                    continue
                src_node = getattr(edge, "start_node", None)
                tgt_node = getattr(edge, "end_node", None)
                src_name = getattr(src_node, "node_name", "") if src_node is not None else ""
                tgt_name = getattr(tgt_node, "node_name", "") if tgt_node is not None else ""
                src_sp = (
                    getattr(getattr(edge, "source_anchor", None), "port_name", "")
                    if getattr(edge, "source_anchor", None) is not None
                    else "default"
                ) or "default"
                tgt_ep = (
                    getattr(getattr(edge, "end_anchor", None), "port_name", "")
                    if getattr(edge, "end_anchor", None) is not None
                    else "default"
                ) or "default"
                if tgt_node is comp_item:
                    up = self._resolve_node_logical_name(src_name, nodes_data) if src_name else ""
                    if up:
                        real_inputs.add((up, src_sp, tgt_ep))
                        # default/data 别名也互相加一份（port 映射可能不同）
                        for ep_alt in {"data", "default"} if tgt_ep in {"data", "default"} else set():
                            if ep_alt != tgt_ep:
                                real_inputs.add((up, src_sp, ep_alt))
                if src_node is comp_item:
                    dn = self._resolve_node_logical_name(tgt_name, nodes_data) if tgt_name else ""
                    if dn:
                        real_outputs.add((src_sp, dn, tgt_ep))
                        for sp_alt in {"default", "node_output"} if src_sp in {"default", "node_output"} else set():
                            if sp_alt != src_sp:
                                real_outputs.add((sp_alt, dn, tgt_ep))

            # 反向校验：内存 routing 中每条 input 端口 entry 必须在 real_inputs 里找到对应外部边
            mem_routing = self._composites.get(comp_id, {}).get("_port_routing", {})
            routing_in = mem_routing.get("input", {}) if isinstance(mem_routing, dict) else {}
            for p_name in list(routing_in.keys()):
                entry = routing_in.get(p_name)
                if not entry:
                    continue
                if isinstance(entry, str):
                    src_path = entry
                    up_id = ""
                    up_port = ""
                else:
                    src_path = entry.get("source_output_path", "") or ""
                    up_id = entry.get("_upstream_node_id", "") or ""
                    up_port = entry.get("_upstream_out_port", "") or ""
                # 从 source_output_path 反推 upstream 目录名
                if not up_id:
                    try:
                        tail_dir = Path(src_path).parent.name if src_path else ""
                    except Exception:
                        tail_dir = ""
                    if tail_dir:
                        # 尝试匹配到 nodes_data
                        for logical, meta in nodes_data.items():
                            mp = (meta or {}).get("path") or ""
                            if Path(mp).name == tail_dir:
                                up_id = logical
                                break
                        if not up_id:
                            # 宽松 match：逻辑名 == tail_dir 或 node_{tail_dir}
                            if tail_dir in nodes_data:
                                up_id = tail_dir
                            elif f"node_{tail_dir}" in nodes_data:
                                up_id = f"node_{tail_dir}"
                # 构造候选匹配三元组集合（p_name 别名全展开 + up_port 别名全展开）
                p_alts = {p_name}
                if p_name in {"data", "default"}:
                    p_alts |= {"data", "default"}
                up_port_alts = {up_port} if up_port else {"default"}
                if up_port in {"", "default"}:
                    up_port_alts.add("default")
                found = False
                for a_up in {up_id} if up_id else {""}:
                    if not a_up:
                        continue
                    for a_uport in up_port_alts:
                        for a_pin in p_alts:
                            if (a_up, a_uport, a_pin) in real_inputs:
                                found = True
                                break
                        if found:
                            break
                    if found:
                        break
                # 最后兜底：如果 real_inputs 根本没有任何 external→comp 边，且 routing 里的该 entry 连 upstream_node_id 都反推不出来 → 判定 stale
                if not found:
                    # 如果没有任何画布边，只有 routing 有条目 → 100% stale 孤儿残留
                    del routing_in[p_name]
                    stale_in_ports_purged.append(p_name)

            routing_out = mem_routing.get("output", {}) if isinstance(mem_routing, dict) else {}
            for p_name in list(routing_out.keys()):
                entry = routing_out.get(p_name) or {}
                if not isinstance(entry, dict):
                    continue
                tgt_node = entry.get("target_node", "") or ""
                tgt_port = entry.get("target_port", "") or "default"
                p_alts = {p_name}
                if p_name in {"default", "node_output"}:
                    p_alts |= {"default", "node_output"}
                tp_alts = {tgt_port} if tgt_port else {"default"}
                found = False
                for a_pout in p_alts:
                    for a_tgt in {tgt_node} if tgt_node else {""}:
                        if not a_tgt:
                            continue
                        for a_tp in tp_alts:
                            if (a_pout, a_tgt, a_tp) in real_outputs:
                                found = True
                                break
                        if found:
                            break
                    if found:
                        break
                if not found:
                    del routing_out[p_name]
                    stale_out_ports_purged.append(p_name)

        if stale_in_ports_purged or stale_out_ports_purged:
            # 发现孤儿配置 → 立刻写 composite.json，防止 debounce 延迟让下次展开又读到
            self._sync_routing_to_config(comp_id)
            logger.warning(
                "[MORPH-PURGE-STALE-CFG] expand comp=%s canvas folded but no edges match; "
                "purged stale input ports=%s stale output ports=%s (orphan config from crashed/non-written debounce)",
                comp_id,
                stale_in_ports_purged,
                stale_out_ports_purged,
            )

        routing = self._get_port_routing(comp_id)

        # 建立 port_name → internal_name 的反查表（expand 时 port→child）
        port_to_internal_in: dict[str, str] = {}
        port_to_internal_out: dict[str, str] = {}
        entry_node_name = self._find_entry_node(comp_id)
        exit_node_name = self._find_exit_node(comp_id)
        for p in comp.get("input_ports", []):
            pn = p.get("port_name", "")
            iname = p.get("internal_node", "")
            if pn and iname:
                port_to_internal_in[pn] = iname
        # 默认端口兜底：data ↔ default 映射到 entry node
        if entry_node_name:
            for alt in ("data", "default"):
                if alt not in port_to_internal_in:
                    port_to_internal_in[alt] = entry_node_name
        for p in comp.get("output_ports", []):
            pn = p.get("port_name", "")
            iname = p.get("internal_node", "")
            if pn and iname:
                port_to_internal_out[pn] = iname
        if exit_node_name:
            for alt in ("default", "node_output"):
                if alt not in port_to_internal_out:
                    port_to_internal_out[alt] = exit_node_name

        # ====== 入向：external → comp.in_port ======
        for in_port, entry in (routing.get("input", {}) or {}).items():
            src_output_path = ""
            tgt_node = ""
            tgt_port_c = "default"
            if isinstance(entry, dict):
                src_output_path = entry.get("source_output_path", "") or ""
                tgt_node = entry.get("target_node", "") or ""
                tgt_port_c = entry.get("target_port", "default") or "default"
            elif isinstance(entry, str):
                src_output_path = entry  # 兼容老版本只存路径字符串的格式
            if not src_output_path:
                continue

            # 解析 upstream_node_id（从 source_output_path 反推）
            upstream_node_id = entry.get("_upstream_node_id", "") if isinstance(entry, dict) else ""
            if not upstream_node_id:
                upstream_node_id = self._extract_node_from_path(src_output_path) or ""
            upstream_out_port = "default"
            if isinstance(entry, dict):
                upstream_out_port = entry.get("_upstream_out_port", "default") or "default"

            # ⚠️ 身份统一必须在 STALE 检查之前：
            # extract_node_from_path 只提取物理目录名（python_node_demo_1），
            # nodes_data 的 key 是逻辑名（node_python_demo_1 前缀），
            # 不先 resolve → 100% 触发 STALE → 整项 purge 丢了
            if upstream_node_id:
                upstream_node_id = self._resolve_node_logical_name(upstream_node_id, nodes_data)

            # STALE 检查 1：upstream_node_id 不在 nodes_data（节点被删）→ 跳过并记录，purge 会统一清
            if upstream_node_id and upstream_node_id not in nodes_data:
                logger.warning(
                    "[MORPH-SKIP-STALE] expand comp=%s in_port=%s upstream=%s not in nodes_data — skip & will purge",
                    comp_id,
                    in_port,
                    upstream_node_id,
                )
                # 标记 stale，purge_stale_routes 钩子会清 composite.in_port
                self._ensure_port_routing(comp_id)
                if self._composites[comp_id]["_port_routing"]["input"].get(in_port) and isinstance(
                    self._composites[comp_id]["_port_routing"]["input"][in_port], dict
                ):
                    self._composites[comp_id]["_port_routing"]["input"][in_port]["_stale"] = True
                continue

            # target_node 没有 → 从反查表查（先 in_port 原名，再 data/default 别名）
            if not tgt_node:
                tgt_node = (
                    port_to_internal_in.get(in_port, "")
                    or port_to_internal_in.get("data", "")
                    or port_to_internal_in.get("default", "")
                )
                if not tgt_node:
                    logger.error(
                        "[MORPH-SKIP-NO-TARGET] expand comp=%s in_port=%s target_node empty & no port→internal map — skip",
                        comp_id,
                        in_port,
                    )
                    continue
            # STALE 检查 2：tgt_node 不在复合子节点列表（子节点被删）
            child_list = comp.get("nodes", []) or []
            if tgt_node not in child_list:
                logger.warning(
                    "[MORPH-SKIP-STALE] expand comp=%s in_port=%s target_child=%s not in comp.nodes — skip & will purge",
                    comp_id,
                    in_port,
                    tgt_node,
                )
                self._ensure_port_routing(comp_id)
                if self._composites[comp_id]["_port_routing"]["input"].get(in_port) and isinstance(
                    self._composites[comp_id]["_port_routing"]["input"][in_port], dict
                ):
                    self._composites[comp_id]["_port_routing"]["input"][in_port]["_stale"] = True
                continue

            morph_list.append(
                {
                    "direction": "input",
                    "in_port": in_port,
                    "upstream_node_id": upstream_node_id,
                    "upstream_out_port": upstream_out_port,
                    "source_output_path": src_output_path,
                    "target_child_name": tgt_node,
                    "target_child_port": tgt_port_c,
                    # 兼容旧字段名（phase C 会 fallback）
                    "source_child_port": tgt_port_c,
                    "external_source_name": upstream_node_id,
                    "external_source_port": upstream_out_port,
                }
            )

        # ====== 出向：comp.out_port → external ======
        for out_port, entry in (routing.get("output", {}) or {}).items():
            if not isinstance(entry, dict):
                continue
            tgt_comp_id = entry.get("target_composite")  # 可为 None（外部普通节点）
            tgt_node = entry.get("target_node", "") or ""
            tgt_port_c = entry.get("target_port", "default") or "default"
            if not tgt_node:
                continue
            # ⚠️ 与 input 方向相同：先 resolve 物理目录名→逻辑名再做任何判定
            if tgt_node:
                tgt_node = self._resolve_node_logical_name(tgt_node, nodes_data)

            child_src_name = port_to_internal_out.get(out_port, "")
            if not child_src_name:
                # 反查不到 → 通过 _find_internal_by_port / _find_exit_node 兜底
                child_src_name = self._find_internal_by_port(comp_id, out_port, "output") or ""
                if not child_src_name and out_port in {"default", "node_output"}:
                    child_src_name = exit_node_name or self._find_exit_node(comp_id)
            if not child_src_name:
                logger.error(
                    "[MORPH-SKIP-NO-SOURCE] expand comp=%s out_port=%s cannot map internal child — skip",
                    comp_id,
                    out_port,
                )
                continue

            child_list = comp.get("nodes", []) or []
            if child_src_name not in child_list:
                logger.warning(
                    "[MORPH-SKIP-STALE] expand comp=%s out_port=%s child_src=%s not in comp.nodes — skip & purge",
                    comp_id,
                    out_port,
                    child_src_name,
                )
                self._ensure_port_routing(comp_id)
                if self._composites[comp_id]["_port_routing"]["output"].get(out_port) and isinstance(
                    self._composites[comp_id]["_port_routing"]["output"][out_port], dict
                ):
                    self._composites[comp_id]["_port_routing"]["output"][out_port]["_stale"] = True
                continue

            morph_list.append(
                {
                    "direction": "output",
                    "out_port": out_port,
                    "child_source_name": child_src_name,
                    "child_source_port": entry.get("_src_child_port", "default") or "default",
                    "downstream_node_id": tgt_node,
                    "downstream_in_port": tgt_port_c,
                    # 兼容旧字段名
                    "source_child_name": child_src_name,
                    "source_child_out_port": entry.get("_src_child_port", "default") or "default",
                    "external_target_name": tgt_node,
                    "external_target_in_port": tgt_port_c,
                    "target_composite": tgt_comp_id,
                }
            )

        logger.info(
            "[MORPH-COLLECT-EXPAND] comp=%s total=%d (input=%d, output=%d)",
            comp_id,
            len(morph_list),
            sum(1 for m in morph_list if m["direction"] == "input"),
            sum(1 for m in morph_list if m["direction"] == "output"),
        )
        # ══════════════════════════════════════════════════════════════
        # Step 末尾：节点名身份统一 — 物理目录名（extract_node_from_path 结果）
        #                         → nodes_data 逻辑名（canvas.nodes 的 key）
        # 防止 PhaseC src_item = canvas.nodes.get("python_node_demo_1") 找不到 →
        #       create_edge 失败 → listen_upper_file 没写 → 断言失败
        # ══════════════════════════════════════════════════════════════
        for m in morph_list:
            if m.get("direction") == "input":
                for k in ("upstream_node_id", "external_source_name"):
                    v = m.get(k)
                    if v:
                        nv = self._resolve_node_logical_name(v, nodes_data)
                        if nv != v:
                            m[k] = nv
                for k in ("target_child_name",):
                    v = m.get(k)
                    if v and v not in nodes_data:
                        # 子节点一般已经是逻辑名，只兜底检查
                        nv = self._resolve_node_logical_name(v, nodes_data)
                        if nv != v:
                            m[k] = nv
            else:  # output
                for k in ("downstream_node_id", "external_target_name"):
                    v = m.get(k)
                    if v:
                        nv = self._resolve_node_logical_name(v, nodes_data)
                        if nv != v:
                            m[k] = nv
                for k in ("child_source_name", "source_child_name"):
                    v = m.get(k)
                    if v and v not in nodes_data:
                        nv = self._resolve_node_logical_name(v, nodes_data)
                        if nv != v:
                            m[k] = nv
        # ══════════════════════════════════════════════════════════════
        # Fallback：若磁盘 composite.json + 内存 routing 全部为空（morph_list=0），
        # 但画布上实际存在连接 comp_item 的可见边（典型：上轮折叠 PhaseC 没写配置成功），
        # 从 canvas.edges 反向推导 morph_list，避免 PhaseC 空跑 → 子节点 listen_upper_file 空 → 断言失败。
        # ══════════════════════════════════════════════════════════════
        if not morph_list and self._canvas and hasattr(self._canvas, "edges"):
            comp_item = self._canvas.nodes.get(comp_id)
            if comp_item is not None:
                nodes_dir = Path(self._project_path) / "nodes"

                def _node_dir_from_logical(logical_name: str) -> str:
                    meta = nodes_data.get(logical_name) or {}
                    p = meta.get("path") or ""
                    if p:
                        try:
                            return Path(p).name
                        except Exception:
                            return logical_name
                    return logical_name

                fb_added = 0
                for edge in list(self._canvas.edges):
                    if not edge.isVisible():
                        continue
                    src_node = edge.start_node
                    tgt_node = edge.end_node
                    src_name = src_node.node_name if hasattr(src_node, "node_name") else ""
                    tgt_name = tgt_node.node_name if hasattr(tgt_node, "node_name") else ""
                    src_sp = (
                        edge.source_anchor.port_name
                        if hasattr(edge, "source_anchor") and edge.source_anchor
                        else "default"
                    ) or "default"
                    tgt_ep = (
                        edge.end_anchor.port_name if hasattr(edge, "end_anchor") and edge.end_anchor else "default"
                    ) or "default"

                    # input: external(src) → comp(tgt)
                    if tgt_node is comp_item and src_name and src_name in nodes_data:
                        up_logical = self._resolve_node_logical_name(src_name, nodes_data)
                        up_dir = _node_dir_from_logical(up_logical)
                        src_out_path = (
                            str((nodes_dir / up_dir / "output.json").resolve())
                            if (nodes_dir / up_dir).exists()
                            else str(nodes_dir / up_dir / "output.json")
                        )
                        tgt_child = (
                            port_to_internal_in.get(tgt_ep, "")
                            or port_to_internal_in.get("data", "")
                            or port_to_internal_in.get("default", "")
                            or self._find_entry_node(comp_id)
                        )
                        if tgt_child:
                            morph_list.append(
                                {
                                    "direction": "input",
                                    "in_port": tgt_ep
                                    if tgt_ep in port_to_internal_in
                                    else (tgt_ep if tgt_ep in {"data", "default"} else "data"),
                                    "upstream_node_id": up_logical,
                                    "upstream_out_port": src_sp,
                                    "source_output_path": src_out_path,
                                    "target_child_name": tgt_child,
                                    "target_child_port": "default",
                                    "source_child_port": "default",
                                    "external_source_name": up_logical,
                                    "external_source_port": src_sp,
                                }
                            )
                            fb_added += 1
                    # output: comp(src) → external(tgt)
                    elif src_node is comp_item and tgt_name and tgt_name in nodes_data:
                        dn_logical = self._resolve_node_logical_name(tgt_name, nodes_data)
                        child_src = (
                            port_to_internal_out.get(src_sp, "")
                            or self._find_internal_by_port(comp_id, src_sp, "output")
                            or self._find_exit_node(comp_id)
                        )
                        if child_src:
                            morph_list.append(
                                {
                                    "direction": "output",
                                    "out_port": src_sp if src_sp in port_to_internal_out else src_sp,
                                    "child_source_name": child_src,
                                    "child_source_port": "default",
                                    "downstream_node_id": dn_logical,
                                    "downstream_in_port": tgt_ep,
                                    "source_child_name": child_src,
                                    "source_child_out_port": "default",
                                    "external_target_name": dn_logical,
                                    "external_target_in_port": tgt_ep,
                                    "target_composite": None,
                                }
                            )
                            fb_added += 1
                if fb_added:
                    logger.info(
                        "[MORPH-COLLECT-EXPAND-FALLBACK] comp=%s canvas-edges fallback added=%d",
                        comp_id,
                        fb_added,
                    )

        if morph_list:
            keys_preview = [
                "{}:{}→{}:{}".format(
                    m.get("upstream_node_id") or m.get("child_source_name") or "?",
                    m.get("in_port") or m.get("child_source_port") or "?",
                    m.get("target_child_name") or m.get("downstream_node_id") or "?",
                    m.get("target_child_port") or m.get("downstream_in_port") or "?",
                )
                for m in morph_list
            ]
            logger.info("[MORPH-COLLECT-EXPAND] comp=%s morph_list=%s", comp_id, keys_preview)
        return morph_list

    def resolve_or_create_comp_in_port(
        self,
        comp_id: str,
        upstream_node_id: str,
        upstream_out_port: str,
        target_child: str,
        target_child_port: str,
    ) -> str:
        """collapse 场景：决定「upstream:up_out → child:child_port」这组映射
        要复用复合 C 已有的哪个 in_port，或新建一个 in_port 名。

        完全匹配（同一 upstream_node_id:upstream_out_port → 同一 target_child:target_child_port）
        → 直接复用；否则新建 in_{idx}。
        """
        routing = self._get_port_routing(comp_id)
        comp = self._composites.get(comp_id, {})
        existing_inputs = routing.get("input", {}) or {}

        # 先找完全匹配：完全相同 upstream + 相同 target → 复用
        for in_port, entry in existing_inputs.items():
            if not isinstance(entry, dict):
                continue
            same_upstream = (
                entry.get("_upstream_node_id") == upstream_node_id
                and entry.get("_upstream_out_port") == upstream_out_port
            )
            # 兼容没有缓存 upstream id 的情况 — 用 source_output_path 反查
            if not same_upstream:
                src_path = entry.get("source_output_path", "") or ""
                cached_up = self._extract_node_from_path(src_path) or ""
                if cached_up == upstream_node_id:
                    same_upstream = upstream_out_port == "default"  # path 无法区分 out_port
            same_target = (
                entry.get("target_node") == target_child
                and (entry.get("target_port") or "default") == target_child_port
            )
            if same_upstream and same_target:
                logger.info(
                    "[MORPH-PORT-REUSE] collapse comp=%s reuse in_port=%s for %s:%s→%s:%s",
                    comp_id,
                    in_port,
                    upstream_node_id,
                    upstream_out_port,
                    target_child,
                    target_child_port,
                )
                return in_port

        # 不完全匹配：新建 in_{idx}，并同步确保 comp input_ports 有对应锚点定义
        existing_names = set(existing_inputs.keys())
        # 同时把内存 comp 的 input_ports 里已经有但 routing 里没写的也算已有
        for p in comp.get("input_ports", []) or []:
            existing_names.add(p.get("port_name", ""))
        cand = ""
        for idx in range(len(existing_names) + 2):
            c = f"in_{idx}" if idx > 0 else "data"  # 第0个输入锚点统一叫 "data"
            if c == "data" and "data" in existing_names:
                cand = "data"  # data 已存在就复用 data
                break
            if c not in existing_names:
                cand = c
                break
        if not cand:
            cand = f"in_{len(existing_names) + 1}"

        # 同步新增 comp input_ports 条目（如果还没有）
        has_port = False
        for p in comp.get("input_ports", []) or []:
            if p.get("port_name") == cand:
                has_port = True
                break
        if not has_port:
            comp.setdefault("input_ports", []).append(
                {
                    "internal_node": target_child,
                    "type": "input",
                    "port_name": cand,
                    "display_name": (f"{upstream_node_id}→{target_child}" if cand != "data" else "数据输入"),
                    "entry_port": None if target_child_port == "default" else target_child_port,
                }
            )
            logger.info("[MORPH-PORT-CREATE] collapse comp=%s new input_port=%s", comp_id, cand)

        # 缓存 upstream 元信息到 routing dict（供后续快速匹配复用）
        self._ensure_port_routing(comp_id)
        self._composites[comp_id]["_port_routing"].setdefault("input", {}).setdefault(cand, {})
        r = self._composites[comp_id]["_port_routing"]["input"][cand]
        if isinstance(r, dict):
            r["_upstream_node_id"] = upstream_node_id
            r["_upstream_out_port"] = upstream_out_port
            r["target_node"] = target_child
            r["target_port"] = target_child_port
        return cand

    def resolve_or_create_comp_out_port(
        self,
        comp_id: str,
        child_source_name: str,
        child_source_port: str,
        downstream_node_id: str,
        downstream_in_port: str,
    ) -> str:
        """collapse 出向端口对称版：child_src:src_port → downstream:dn_port
        决定复用 comp 的哪个 out_port，或新建。"""
        routing = self._get_port_routing(comp_id)
        comp = self._composites.get(comp_id, {})
        existing_outputs = routing.get("output", {}) or {}

        for out_port, entry in existing_outputs.items():
            if not isinstance(entry, dict):
                continue
            same_target = (
                entry.get("target_node") == downstream_node_id
                and (entry.get("target_port") or "default") == downstream_in_port
            )
            # 源端判定：用 target_composite/原 routing 里隐式的 source（这里简化直接按 target 匹配）
            if same_target and entry.get("_src_child") == child_source_name:
                logger.info(
                    "[MORPH-PORT-OUT-REUSE] collapse comp=%s reuse out_port=%s",
                    comp_id,
                    out_port,
                )
                return out_port

        existing_names = set(existing_outputs.keys())
        for p in comp.get("output_ports", []) or []:
            existing_names.add(p.get("port_name", ""))

        # 默认第0个出口锚点叫 {exit_node}_out（与 _identify_ports 保持一致），其余 out_{idx}
        cand = f"{child_source_name}_out"
        if cand in existing_names:
            for idx in range(1, len(existing_names) + 3):
                c2 = f"{child_source_name}_out_{idx}"
                if c2 not in existing_names:
                    cand = c2
                    break
        # 同步补 comp.output_ports 条目
        has_port = False
        for p in comp.get("output_ports", []) or []:
            if p.get("port_name") == cand:
                has_port = True
                break
        if not has_port:
            comp.setdefault("output_ports", []).append(
                {
                    "internal_node": child_source_name,
                    "type": "output",
                    "port_name": cand,
                    "display_name": child_source_name,
                }
            )
            logger.info("[MORPH-PORT-OUT-CREATE] collapse comp=%s new output_port=%s", comp_id, cand)

        # 缓存匹配用元信息
        self._ensure_port_routing(comp_id)
        self._composites[comp_id]["_port_routing"].setdefault("output", {}).setdefault(cand, {})
        r = self._composites[comp_id]["_port_routing"]["output"][cand]
        if isinstance(r, dict):
            r["_src_child"] = child_source_name
            r["_src_child_port"] = child_source_port
            r["target_node"] = downstream_node_id
            r["target_port"] = downstream_in_port
        return cand

    def collect_collapse_morph_list(self, comp_id: str) -> list[dict]:
        """collapse 阶段A：在所有子节点 UI 边/配置/EdgeKey 全部完好未动时机，
        从磁盘配置（不是内存）+ MembershipSM 子节点列表读真相，
        全量抄 morph_list 到内存。后面清子配置不影响此信息。

        NOTE: 不扫 scene.items() —— 权威来源 = 子节点磁盘 node_config.json（不是内存缓存）
        """
        morph_list: list[dict] = []
        comp = self._composites.get(comp_id, {})
        child_names = list(comp.get("nodes", []) or [])
        nodes_data = self._nodes_data_global()
        nodes_dir = Path(self._project_path) / "nodes"
        comp_child_set = set(child_names)

        for child_name in child_names:
            cfg_path = Path(get_config_path(str(Path(self._project_path) / "nodes" / child_name)))
            try:
                with cfg_path.open(encoding="utf-8") as f:
                    child_cfg = json.load(f) or {}
            except (OSError, json.JSONDecodeError):
                continue  # 损坏配置跳过（用户可能手动删了文件，purge 会清）

            # ---- 入向：child 的 listen_upper_file + port_mappings ----
            luf = child_cfg.get("listen_upper_file", "") or ""
            if luf:
                upstream_node_id = self._extract_node_from_path(luf) or ""
                # ⚠️ 身份统一在 comp_child_set / nodes_data 判定之前：
                # extract_node_from_path → 物理目录名（如 python_node_demo_1），
                # nodes_data key 是逻辑名（node_python_demo_1），不先 resolve 会误判为外部节点不存在！
                if upstream_node_id:
                    upstream_node_id = self._resolve_node_logical_name(upstream_node_id, nodes_data)
                if upstream_node_id and upstream_node_id not in comp_child_set:
                    # upstream 在复合外部 → 需要 morph 成 external→comp
                    # STALE：upstream 不在 nodes_data（被删）→ 跳过，purge_stale_routes 后续清子
                    if upstream_node_id not in nodes_data:
                        logger.warning(
                            "[MORPH-SKIP-STALE] collapse child=%s upstream=%s not in nodes_data — skip morph, will clear child luf",
                            child_name,
                            upstream_node_id,
                        )
                        continue
                    comp_in_port = self.resolve_or_create_comp_in_port(
                        comp_id,
                        upstream_node_id,
                        "default",
                        child_name,
                        "default",
                    )
                    morph_list.append(
                        {
                            "direction": "input",
                            "comp_in_port": comp_in_port,
                            "upstream_node_id": upstream_node_id,
                            "upstream_out_port": "default",
                            "source_output_path": luf,
                            "target_child_name": child_name,
                            "target_child_port": "default",
                        }
                    )

            pm = child_cfg.get("port_mappings", {}) or {}
            if isinstance(pm, dict):
                for child_in_port, pm_path in pm.items():
                    if not isinstance(pm_path, str) or not pm_path:
                        continue
                    up_node = self._extract_node_from_path(pm_path) or ""
                    # ⚠️ 同上：先 resolve 再判外部/存在性
                    if up_node:
                        up_node = self._resolve_node_logical_name(up_node, nodes_data)
                    if up_node and up_node not in comp_child_set and up_node in nodes_data:
                        cport = self.resolve_or_create_comp_in_port(
                            comp_id,
                            up_node,
                            "default",
                            child_name,
                            child_in_port,
                        )
                        morph_list.append(
                            {
                                "direction": "input",
                                "comp_in_port": cport,
                                "upstream_node_id": up_node,
                                "upstream_out_port": "default",
                                "source_output_path": pm_path,
                                "target_child_name": child_name,
                                "target_child_port": child_in_port,
                            }
                        )

            # ---- 出向：child.out_connections → 外部下游 ----
            out_conns = child_cfg.get("out_connections", {}) or {}
            if isinstance(out_conns, dict):
                for src_port_key, target in out_conns.items():
                    if not isinstance(target, str) or not target:
                        continue
                    parts = target.split("|", 1)
                    dn_node = parts[0]
                    dn_port = parts[1] if len(parts) > 1 else "default"
                    # ⚠️ 兜底：out_connections 写入时若也写成物理目录名，此处 resolve 一次保证安全
                    if dn_node:
                        dn_node = self._resolve_node_logical_name(dn_node, nodes_data)
                    if dn_node and dn_node not in comp_child_set and dn_node in nodes_data:
                        comp_out_port = self.resolve_or_create_comp_out_port(
                            comp_id,
                            child_name,
                            src_port_key,
                            dn_node,
                            dn_port,
                        )
                        morph_list.append(
                            {
                                "direction": "output",
                                "comp_out_port": comp_out_port,
                                "child_source_name": child_name,
                                "child_source_port": src_port_key,
                                "downstream_node_id": dn_node,
                                "downstream_in_port": dn_port,
                            }
                        )

        logger.info(
            "[MORPH-COLLECT-COLLAPSE] comp=%s total=%d (input=%d, output=%d)",
            comp_id,
            len(morph_list),
            sum(1 for m in morph_list if m["direction"] == "input"),
            sum(1 for m in morph_list if m["direction"] == "output"),
        )
        # ══════════════════════════════════════════════════════════════
        # Step 末尾：节点名身份统一 — 物理目录名 → nodes_data 逻辑名
        # （collapse 节点名一般来自 nodes_data，但是 listen_upper_file 反查 upstream 时
        #  extract_node_from_path 会返回目录名，此处同样做 normalize）
        # ══════════════════════════════════════════════════════════════
        for m in morph_list:
            if m.get("direction") == "input":
                for k in ("upstream_node_id", "external_source_name"):
                    v = m.get(k)
                    if v:
                        nv = self._resolve_node_logical_name(v, nodes_data)
                        if nv != v:
                            m[k] = nv
                for k in ("target_child_name",):
                    v = m.get(k)
                    if v and v not in nodes_data:
                        nv = self._resolve_node_logical_name(v, nodes_data)
                        if nv != v:
                            m[k] = nv
            else:  # output
                for k in ("downstream_node_id", "external_target_name"):
                    v = m.get(k)
                    if v:
                        nv = self._resolve_node_logical_name(v, nodes_data)
                        if nv != v:
                            m[k] = nv
                for k in ("child_source_name", "source_child_name"):
                    v = m.get(k)
                    if v and v not in nodes_data:
                        nv = self._resolve_node_logical_name(v, nodes_data)
                        if nv != v:
                            m[k] = nv

        # ══════════════════════════════════════════════════════════════
        # Fallback：若 child 磁盘配置全部为空（morph_list=0），但画布上实际有
        # external ↔ child 的跨边界可见边（典型：上轮 expand PhaseC 没写配置成功），
        # 从 canvas.edges 反向推导 morph_list，避免 PhaseB 删了边但 PhaseC 不重建、
        # 也不写 composite.json → 复合态 connection 丢失 → 下次 expand 再爆 STALE。
        # ══════════════════════════════════════════════════════════════
        if not morph_list and self._canvas and hasattr(self._canvas, "edges"):
            nodes_dir = Path(self._project_path) / "nodes"

            def _node_dir_from_logical(logical_name: str) -> str:
                meta = nodes_data.get(logical_name) or {}
                p = meta.get("path") or ""
                if p:
                    try:
                        return Path(p).name
                    except Exception:
                        return logical_name
                return logical_name

            fb_added = 0
            for edge in list(self._canvas.edges):
                if not edge.isVisible():
                    continue
                src_node = edge.start_node
                tgt_node = edge.end_node
                src_name = src_node.node_name if hasattr(src_node, "node_name") else ""
                tgt_name = tgt_node.node_name if hasattr(tgt_node, "node_name") else ""
                src_sp = (
                    edge.source_anchor.port_name if hasattr(edge, "source_anchor") and edge.source_anchor else "default"
                ) or "default"
                tgt_ep = (
                    edge.end_anchor.port_name if hasattr(edge, "end_anchor") and edge.end_anchor else "default"
                ) or "default"
                src_in = src_name in comp_child_set
                tgt_in = tgt_name in comp_child_set
                if not (src_in ^ tgt_in):
                    continue  # 两边都内部 or 两边都外部 → 不是跨边界，跳过

                # Case A：external(src) → child(tgt)  入向
                if not src_in and tgt_in and src_name and src_name in nodes_data:
                    up_logical = self._resolve_node_logical_name(src_name, nodes_data)
                    up_dir = _node_dir_from_logical(up_logical)
                    src_out_path = (
                        str((nodes_dir / up_dir / "output.json").resolve())
                        if (nodes_dir / up_dir).exists()
                        else str(nodes_dir / up_dir / "output.json")
                    )
                    child_port = "default" if tgt_ep in {"default", "data"} else tgt_ep
                    comp_in_port = self.resolve_or_create_comp_in_port(
                        comp_id,
                        up_logical,
                        src_sp,
                        tgt_name,
                        child_port,
                    )
                    morph_list.append(
                        {
                            "direction": "input",
                            "comp_in_port": comp_in_port,
                            "upstream_node_id": up_logical,
                            "upstream_out_port": src_sp,
                            "source_output_path": src_out_path,
                            "target_child_name": tgt_name,
                            "target_child_port": child_port,
                        }
                    )
                    fb_added += 1
                # Case B：child(src) → external(tgt)  出向
                elif src_in and not tgt_in and tgt_name and tgt_name in nodes_data:
                    dn_logical = self._resolve_node_logical_name(tgt_name, nodes_data)
                    child_src_port = src_sp
                    comp_out_port = self.resolve_or_create_comp_out_port(
                        comp_id,
                        src_name,
                        child_src_port,
                        dn_logical,
                        tgt_ep,
                    )
                    morph_list.append(
                        {
                            "direction": "output",
                            "comp_out_port": comp_out_port,
                            "child_source_name": src_name,
                            "child_source_port": child_src_port,
                            "downstream_node_id": dn_logical,
                            "downstream_in_port": tgt_ep,
                        }
                    )
                    fb_added += 1
            if fb_added:
                logger.info(
                    "[MORPH-COLLECT-COLLAPSE-FALLBACK] comp=%s canvas-edges fallback added=%d",
                    comp_id,
                    fb_added,
                )

        # 结束前补打一次详细日志（含 fallback 后）
        if morph_list:
            keys_preview = [
                "{}:{}→{}:{}".format(
                    m.get("upstream_node_id") or m.get("child_source_name") or "?",
                    m.get("comp_in_port") or m.get("child_source_port") or "?",
                    m.get("target_child_name") or m.get("downstream_node_id") or "?",
                    m.get("target_child_port") or m.get("downstream_in_port") or "?",
                )
                for m in morph_list
            ]
            logger.info("[MORPH-COLLECT-COLLAPSE] comp=%s (final) morph_list=%s", comp_id, keys_preview)

        return morph_list

    def _assert_mutex_consistency(self, comp_id: str, morph_list: list[dict], expanded: bool) -> None:
        """互斥硬断言（expand/collapse morph 步骤5执行）。

        expanded=True （展开态）：
            composite.json.external_connections.input[in_port] 必空；
            item.target_child_name 的 listen_upper_file / port_mappings == source_output_path。
        expanded=False（折叠态）：
            composite.in_port.source_output_path 非空 → 对应 target_child:target_port 必空。
        互斥违背 = fail-fast AssertionError，不进用户态（防止后续 expand/collapse 循环歧义）。
        """
        routing = self._get_port_routing(comp_id)
        comp = self._composites.get(comp_id, {})
        child_names = set(comp.get("nodes", []) or [])

        for item in morph_list:
            if item["direction"] == "input":
                in_port = item.get("in_port") or item.get("comp_in_port") or ""
                src_path = item.get("source_output_path", "")
                tgt_child = item.get("target_child_name", "")
                tgt_child_port = item.get("target_child_port", "default") or "default"

                if expanded:
                    # 展开态：composite input 该端口必须空
                    r_entry = (routing.get("input", {}) or {}).get(in_port)
                    r_path = ""
                    if isinstance(r_entry, dict):
                        r_path = r_entry.get("source_output_path", "") or ""
                    elif isinstance(r_entry, str):
                        r_path = r_entry
                    if r_path:
                        raise AssertionError(
                            f"[MUTEX-VIOLATION expand] comp={comp_id} in_port={in_port} "
                            f"composite.source_output_path NOT EMPTY={r_path[:60]}! "
                            f"(target_child={tgt_child}) — 互斥违背：两边同时写同一路由"
                        )
                    # 展开态：子 listen_upper_file / port_mappings 必须是 src_path
                    if tgt_child:
                        cfg_path = Path(get_config_path(str(Path(self._project_path) / "nodes" / tgt_child)))
                        try:
                            with cfg_path.open(encoding="utf-8") as f:
                                ccfg = json.load(f) or {}
                        except (OSError, json.JSONDecodeError):
                            ccfg = {}
                        if tgt_child_port == "default":
                            actual = ccfg.get("listen_upper_file", "") or ""
                            if actual != src_path:
                                raise AssertionError(
                                    f"[MUTEX-VIOLATION expand] comp={comp_id} "
                                    f"child={tgt_child} listen_upper_file={actual[:60]} "
                                    f"≠ expected={src_path[:60]}"
                                )
                        else:
                            pm = ccfg.get("port_mappings", {}) or {}
                            actual = pm.get(tgt_child_port, "") or ""
                            if actual != src_path:
                                raise AssertionError(
                                    f"[MUTEX-VIOLATION expand] comp={comp_id} "
                                    f"child={tgt_child} port_mappings[{tgt_child_port}]={actual[:60]} "
                                    f"≠ expected={src_path[:60]}"
                                )
                else:
                    # 折叠态：composite.in_port 有值 → 子对应端口必须空
                    if tgt_child and tgt_child in child_names and src_path:
                        cfg_path = Path(get_config_path(str(Path(self._project_path) / "nodes" / tgt_child)))
                        try:
                            with cfg_path.open(encoding="utf-8") as f:
                                ccfg = json.load(f) or {}
                        except (OSError, json.JSONDecodeError):
                            ccfg = {}
                        if tgt_child_port == "default":
                            actual = ccfg.get("listen_upper_file", "") or ""
                        else:
                            pm = ccfg.get("port_mappings", {}) or {}
                            actual = pm.get(tgt_child_port, "") or ""
                        if actual:
                            raise AssertionError(
                                f"[MUTEX-VIOLATION collapse] comp={comp_id} in_port={in_port} "
                                f"composite has src_path={src_path[:60]} BUT "
                                f"child={tgt_child}.{tgt_child_port}={actual[:60]} NOT EMPTY — 互斥违背"
                            )

            # output direction 互斥对称（简化检查：只检查 composite.output 有值时 child.out_connections 对应空）
            if item["direction"] == "output" and not expanded:
                child_src = item.get("child_source_name", "")
                child_src_port = item.get("child_source_port", "default") or "default"
                if child_src and child_src in child_names:
                    cfg_path = Path(get_config_path(str(Path(self._project_path) / "nodes" / child_src)))
                    try:
                        with cfg_path.open(encoding="utf-8") as f:
                            ccfg = json.load(f) or {}
                    except (OSError, json.JSONDecodeError):
                        ccfg = {}
                    out_conns = ccfg.get("out_connections", {}) or {}
                    if child_src_port in out_conns and out_conns[child_src_port]:
                        dn_node = item.get("downstream_node_id", "")
                        raise AssertionError(
                            f"[MUTEX-VIOLATION collapse output] comp={comp_id} "
                            f"child_src={child_src} out_connections[{child_src_port}]={out_conns[child_src_port]} "
                            f"NOT EMPTY (→ dn={dn_node}) — 互斥违背"
                        )

        logger.info("[MORPH-MUTEX-ASSERT] comp=%s expanded=%s — OK (%d entries)", comp_id, expanded, len(morph_list))

    def is_node_in_composite(self, node_name: str) -> bool:
        return self._find_composite_of_node(node_name) is not None

    def _detach_from_user_groups(self, node_names: list[str]):
        """将节点从用户手动创建的节点组中移出。"""
        if not self._group_manager:
            return
        for n in node_names:
            current_group = self._group_manager.node_to_group.get(n, "")
            if current_group and not current_group.startswith(GROUP_PREFIX):
                try:
                    self._group_manager.remove_nodes_from_group(current_group, [n])
                except (RuntimeError, ValueError, KeyError):
                    pass

    def _comp_venv_dir(self, comp_id: str) -> str:
        """获取复合节点的 venv 目录路径 — composite_nodes/{comp_id}/venv/。"""
        return comp_venv_path(self._project_path, comp_id)

    # ── composite_nodes/ 目录管理 ──

    @staticmethod
    def _comp_config_dir(project_path: str, comp_id: str) -> Path:
        """返回 composite_nodes/<comp_id>/ 目录路径。"""
        return Path(project_path) / COMPOSITE_NODES_DIR / comp_id

    @staticmethod
    def _comp_config_path(project_path: str, comp_id: str) -> Path:
        """返回 composite_nodes/<comp_id>/composite.json 路径。"""
        return Path(project_path) / COMPOSITE_NODES_DIR / comp_id / "composite.json"

    @staticmethod
    def _comp_registry_path(project_path: str, comp_id: str) -> Path:
        """返回 composite_nodes/<comp_id>/node_registry.json 路径。"""
        return Path(project_path) / COMPOSITE_NODES_DIR / comp_id / "node_registry.json"

    @staticmethod
    def _comp_logs_dir(project_path: str, comp_id: str) -> Path:
        """返回 composite_nodes/<comp_id>/logs/ 目录路径。"""
        return Path(project_path) / COMPOSITE_NODES_DIR / comp_id / "logs"

    @staticmethod
    def _comp_pipeline_path(project_path: str, comp_id: str) -> Path:
        """返回 composite_nodes/<comp_id>/pipeline.json 路径。"""
        return Path(project_path) / COMPOSITE_NODES_DIR / comp_id / "pipeline.json"

    def _touch_pipe_signal(self, comp_id: str):
        """在 composite_nodes/<comp_id>/ 写入 .pipe 信号文件。

        运行中的编排器检测到此文件后会自动重新加载 pipeline.json。
        """
        pipe_path = self._comp_config_dir(self._project_path, comp_id) / ".pipe"
        try:
            pipe_path.write_text("", encoding="utf-8")
        except OSError:
            pass

    @staticmethod
    def _comp_output_dir(project_path: str, comp_id: str) -> Path:
        """返回 composite_nodes/<comp_id>/output/ 目录路径。"""
        return Path(project_path) / COMPOSITE_NODES_DIR / comp_id / "output"

    def _sync_pipeline(self, comp_id: str):
        """从 composite.json 同步生成 pipeline.json（纯 DAG 拓扑）。

        pipeline.json 是 orchestrator.py 的运行时数据源，
        DAG 变更时仅需更新此文件，不必重新生成 orchestrator.py。
        """
        cfg = self._load_composite_config(comp_id)
        if not cfg:
            return

        # 从 node_registry.json 获取节点实际路径（处理注册名≠目录名的情况）
        node_paths = {}
        registry_path = Path(self._project_path) / "node_registry.json"
        if registry_path.exists():
            try:
                with open(registry_path, encoding="utf-8") as f:
                    registry = json.load(f)
                for nid, info in registry.get("nodes", {}).items():
                    p = info.get("path", "")
                    if p:
                        node_paths[nid] = p
            except Exception:
                pass

        pipeline = {
            "comp_id": comp_id,
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "nodes": [
                {
                    "name": n["name"],
                    "path": node_paths.get(n["name"]) or n.get("path", f"nodes/{n['name']}"),
                    "module": f"nodes.{n['name']}.main",
                }
                for n in cfg.get("nodes", [])
            ],
            "edges": cfg.get("edges", []),
            "input_filter_rules": cfg.get("input_filter_rules", {}),
            "external_connections": self._get_port_routing(comp_id),
        }
        pipeline_path = self._comp_pipeline_path(self._project_path, comp_id)
        with pipeline_path.open("w", encoding="utf-8") as f:
            json.dump(pipeline, f, ensure_ascii=False, indent=2)

    def _create_comp_config_dir(
        self,
        comp_id: str,
        node_names: list[str],
        edges_list: list[dict],
        ports: dict,
        display_name: str,
        common_lang: str,
        cx: float,
        cy: float,
        original_positions: dict,
        input_filter_rules: dict | None = None,
    ):
        """创建 composite_nodes/<comp_id>/ 完整的目录结构并写入所有文件。

        目录结构:
          composite_nodes/<comp_id>/
            composite.json
            node_registry.json
            logs/
        """
        comp_dir = self._comp_config_dir(self._project_path, comp_id)
        logs_dir = comp_dir / "logs"
        output_dir = comp_dir / "output"
        comp_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. composite.json
        composite_config = {
            "comp_id": comp_id,
            "display_name": display_name,
            "language": common_lang,
            "version": 1,
            "runtime": {
                "mode": self._composites.get(comp_id, {}).get("runtime", "inprocess"),
                "python_exe": None,
            },
            "nodes": [
                {
                    "name": n,
                    "path": f"nodes/{n}",
                    "order": i,
                    "entry": "listener.py",
                    "resource_limit": {},
                }
                for i, n in enumerate(node_names)
            ],
            "edges": edges_list,
            "ports": {
                "input": ports.get("input_ports", []),
                "output": ports.get("output_ports", []),
            },
            "resource_group": {
                "group_id": f"grp_{comp_id.replace('composite_', '')}",
                "enabled": True,
                "composite_resource_limit": {},
            },
            "canvas_meta": {
                "position": {"x": cx, "y": cy},
                "original_positions": original_positions,
            },
            "input_filter_rules": input_filter_rules or {},
        }
        self._write_composite_config(comp_id, composite_config)

        # 2. node_registry.json
        now_ts = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        registry = {
            "group_id": composite_config["resource_group"]["group_id"],
            "composite_name": display_name or comp_id,
            "comp_id": comp_id,
            "registered_at": now_ts,
            "nodes": {
                n: {
                    "path": f"nodes/{n}",
                    "status": "idle",
                    "last_pid": None,
                    "launched_by": None,
                    "last_started": None,
                    "independent_runs": 0,
                }
                for n in node_names
            },
        }
        self._write_registry(comp_id, registry)

    def _write_composite_config(self, comp_id: str, config: dict):
        """写入 composite.json。"""
        from ui.core.edge.canonical_edge_resolver import get_global_mtime_cache

        cfg_path = self._comp_config_path(self._project_path, comp_id)
        with cfg_path.open("w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        try:
            get_global_mtime_cache().invalidate(str(cfg_path))
        except Exception:
            pass

    def _load_composite_config(self, comp_id: str) -> dict | None:
        """加载 composite.json，损坏时从 node_clusters.json 重建。"""
        cfg_path = self._comp_config_path(self._project_path, comp_id)
        try:
            with cfg_path.open(encoding="utf-8") as f:
                data = json.load(f)
            if "nodes" not in data or "comp_id" not in data:
                raise ValueError("缺少必填字段 nodes / comp_id")
            return data
        except (OSError, ValueError, json.JSONDecodeError):
            logger.warning("composite.json 损坏，从 node_clusters.json 重建 %s", comp_id)
            return self._rebuild_composite_config(comp_id)

    def _rebuild_composite_config(self, comp_id: str) -> dict | None:
        """从 node_clusters.json 条目重建 composite.json。"""
        comp = self._composites.get(comp_id)
        if not comp:
            return None
        node_names = comp.get("nodes", [])
        ports = {
            "input": comp.get("input_ports", []),
            "output": comp.get("output_ports", []),
        }
        edges = comp.get("_internal_edges", [])
        display_name = comp.get("display_name", "")
        common_lang = comp.get("language", "Python")
        pos = comp.get("canvas_position", {"x": 0, "y": 0})
        orig = comp.get("original_positions", {})
        # Recreate directory and config
        self._create_comp_config_dir(
            comp_id,
            node_names,
            edges,
            ports,
            display_name,
            common_lang,
            pos["x"],
            pos["y"],
            orig,
        )
        return self._load_composite_config(comp_id)

    def _write_registry(self, comp_id: str, registry: dict):
        """写入 node_registry.json。"""
        reg_path = self._comp_registry_path(self._project_path, comp_id)
        with reg_path.open("w", encoding="utf-8") as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)

    def _load_registry(self, comp_id: str) -> dict | None:
        """加载 node_registry.json。"""
        reg_path = self._comp_registry_path(self._project_path, comp_id)
        try:
            with reg_path.open(encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def _update_registry_node(
        self,
        comp_id: str,
        node_name: str,
        status: str | None = None,
        pid: int | None = None,
        launched_by: str | None = None,
    ):
        """更新 node_registry.json 中某个节点的运行时状态。"""
        registry = self._load_registry(comp_id)
        if not registry or node_name not in registry.get("nodes", {}):
            return
        entry = registry["nodes"][node_name]
        if status is not None:
            entry["status"] = status
        if pid is not None:
            entry["last_pid"] = pid
        if launched_by is not None:
            entry["launched_by"] = launched_by
        if status == "running" and launched_by == "user":
            entry["independent_runs"] = entry.get("independent_runs", 0) + 1
            entry["last_started"] = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if status == "idle":
            entry["last_pid"] = None
            entry["launched_by"] = None
        self._write_registry(comp_id, registry)

    @staticmethod
    def _compute_structure_fingerprint(comp: dict) -> str:
        """对复合节点的 nodes[] + edges[] 做 SHA256 前 8 位。

        相同结构 → 相同指纹；结构变化 → 指纹不同。
        """
        nodes = sorted(comp.get("nodes", []))
        edges = sorted((e.get("from", ""), e.get("to", "")) for e in comp.get("edges", comp.get("_internal_edges", [])))
        payload = json.dumps({"nodes": nodes, "edges": edges}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:8]

    def _decompress_cleanup(self, comp_id: str):
        """解压缩时清理 composite_nodes/<comp_id>/，日志先存档。

        规则:
          - logs/ → 存档到 .archive/<comp_id>_<fingerprint>_<timestamp>/
          - venv/ → 直接删除（已在 remove_comp_env 处理）
          - 其他所有文件 → 删除
          - node_clusters.json 条目 → 调用方处理
        """
        comp_dir = self._comp_config_dir(self._project_path, comp_id)
        logs_dir = comp_dir / "logs"

        # 存档日志
        if logs_dir.exists():
            log_files = list(logs_dir.glob("*.log"))
            if log_files:
                comp = self._composites.get(comp_id, {})
                fingerprint = self._compute_structure_fingerprint(comp)
                ts = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
                archive_dir = (
                    Path(self._project_path) / COMPOSITE_NODES_DIR / ARCHIVE_DIR / f"{comp_id}_{fingerprint}_{ts}"
                )
                archive_dir.mkdir(parents=True, exist_ok=True)

                # 同时存档 composite.json 快照
                cfg_src = comp_dir / "composite.json"
                if cfg_src.exists():
                    try:
                        shutil.copy2(cfg_src, archive_dir / "composite.json")
                    except OSError:
                        pass
                for lf in log_files:
                    try:
                        shutil.copy2(lf, archive_dir / lf.name)
                    except OSError:
                        pass
                self._prune_archives(comp_id)

        # 删除整个复合节点配置目录
        try:
            shutil.rmtree(comp_dir, ignore_errors=True)
        except OSError:
            pass

    def _prune_archives(self, comp_id: str):
        """超出最大存档数的旧存档自动删除。"""
        import os as _os

        archive_base = Path(self._project_path) / COMPOSITE_NODES_DIR / ARCHIVE_DIR
        if not archive_base.exists():
            return
        archives = sorted(
            archive_base.glob(f"{comp_id}_*"),
            key=lambda p: _os.path.getmtime(str(p)),
            reverse=True,
        )
        for old in archives[ARCHIVE_MAX_COUNT:]:
            try:
                shutil.rmtree(old, ignore_errors=True)
            except OSError:
                pass

    def _migrate_existing_composites(self):
        """BNOS 启动时：为已有复合节点创建 composite.json + node_registry.json（如果缺失）。"""
        for comp_id, comp in self._composites.items():
            cfg_path = self._comp_config_path(self._project_path, comp_id)
            if not cfg_path.exists():
                node_names = comp.get("nodes", [])
                edges = comp.get("_internal_edges", [])
                ports = {
                    "input": comp.get("input_ports", []),
                    "output": comp.get("output_ports", []),
                }
                display_name = comp.get("display_name", "")
                common_lang = comp.get("language", "Python")
                pos = comp.get("canvas_position", {"x": 0, "y": 0})
                orig = comp.get("original_positions", {})
                self._create_comp_config_dir(
                    comp_id,
                    node_names,
                    edges,
                    ports,
                    display_name,
                    common_lang,
                    pos["x"],
                    pos["y"],
                    orig,
                )
                logger.info("已迁移复合节点 %s", comp_id)
                # 迁移旧 venv（从 nodes/{name}_venv/ 移动到 composite_nodes/comp_id/venv/）
                new_venv_path = self._comp_config_dir(self._project_path, comp_id) / "venv"
                if not new_venv_path.exists():
                    old_venv_candidates = [
                        Path(self._project_path) / "nodes" / f"{display_name}_venv" / "venv" if display_name else None,
                        Path(self._project_path) / "nodes" / f"__comp__{comp_id}_venv" / "venv",
                    ]
                    for old_venv in old_venv_candidates:
                        if old_venv and old_venv.exists():
                            try:
                                old_parent = old_venv.parent
                                shutil.move(str(old_parent), str(new_venv_path.parent))
                                logger.info("已迁移复合节点 venv: %s → %s", old_parent, new_venv_path.parent)
                                break
                            except OSError:
                                pass

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
                except (RuntimeError, KeyError, OSError):
                    pass

    def _canvas_compress(
        self, comp_id: str, node_names: list, cx: float, cy: float, display_name: str = "", ports: dict = None
    ):
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
            src_name = edge.start_node.node_name if hasattr(edge.start_node, "node_name") else ""
            tgt_name = edge.end_node.node_name if hasattr(edge.end_node, "node_name") else ""
            src_in = src_name in node_set
            tgt_in = tgt_name in node_set
            if src_in and tgt_in:
                internal_edge_info.append(
                    {
                        "src": src_name,
                        "tgt": tgt_name,
                        "src_port": getattr(edge, "source_port_name", ""),
                        "tgt_port": getattr(edge, "target_port_name", ""),
                    }
                )
                edge.setVisible(False)
            elif src_in != tgt_in:
                # One endpoint internal, one external
                external_edge_info.append(
                    {
                        "src": src_name,
                        "tgt": tgt_name,
                        "src_port": getattr(edge, "source_port_name", ""),
                        "tgt_port": getattr(edge, "target_port_name", ""),
                    }
                )
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

        # Create new edges from composite node to external nodes
        from ui.canvas.items.edge_item import EdgeItem

        for info in external_edge_info:
            # Determine if this is composite output → external or external → composite input
            src_in = info["src"] in node_set
            tgt_in = info["tgt"] in node_set

            if src_in and not tgt_in:
                # Composite output → external target
                # Find the output port that corresponds to the internal source node
                for port in output_ports:
                    if port["internal_node"] == info["src"]:
                        source_anchor = comp_item.find_anchor_by_port(port["port_name"], "output")
                        if source_anchor:
                            target_item = self._canvas.nodes.get(info["tgt"])
                            if target_item:
                                new_edge = EdgeItem(
                                    comp_item,
                                    target_item,
                                    self._canvas,
                                    source_anchor=source_anchor,
                                    target_anchor=target_item.input_anchor,
                                )
                                self._canvas.scene.addItem(new_edge)
                                self._canvas.edges.append(new_edge)
                                new_edge.update_path()
                                break

            elif not src_in and tgt_in:
                # External source → composite input
                for port in input_ports:
                    if port["internal_node"] == info["tgt"]:
                        target_anchor = comp_item.find_anchor_by_port(port["port_name"], "input")
                        if target_anchor:
                            source_item = self._canvas.nodes.get(info["src"])
                            if source_item:
                                new_edge = EdgeItem(
                                    source_item,
                                    comp_item,
                                    self._canvas,
                                    source_anchor=source_item.output_anchor,
                                    target_anchor=target_anchor,
                                )
                                self._canvas.scene.addItem(new_edge)
                                self._canvas.edges.append(new_edge)
                                new_edge.update_path()
                                break

    def _canvas_decompress(self, comp_id: str, node_names: list, positions: dict):
        """Canvas: remove composite node, restore original nodes and internal edges.

        Also remaps any edges that were connected to the composite node's ports
        (created AFTER compression) to the corresponding internal nodes, so they
        don't become ghost edges when comp_item is removed from the scene.
        """

        from ui.canvas.items.edge_item import EdgeItem

        comp = self._composites.get(comp_id, {})
        comp_item = self._canvas.nodes.get(comp_id)

        # ── Fix: remap edges connected to composite node's ports BEFORE removing comp_item ──
        if comp_item:
            for edge in list(self._canvas.edges):
                # External node → composite input port
                if edge.end_node is comp_item:
                    tgt_anchor = getattr(edge, "_target_anchor", None)
                    port_name = getattr(tgt_anchor, "port_name", "")
                    internal_name = self._find_internal_by_port(comp_id, port_name, "input")
                    if internal_name:
                        internal_item = self._canvas.nodes.get(internal_name)
                        if internal_item:
                            new_edge = EdgeItem(
                                edge.start_node,
                                internal_item,
                                self._canvas,
                                target_anchor=internal_item.input_anchor,
                                source_anchor=getattr(edge, "_source_anchor", None),
                            )
                            if hasattr(edge, "_waypoints") and edge._waypoints:
                                new_edge._waypoints = list(edge._waypoints)
                            self._canvas.scene.addItem(new_edge)
                            self._canvas.edges.append(new_edge)
                            new_edge.update_path()
                            # Remove old ghost edge
                            if edge in self._canvas.edges:
                                self._canvas.edges.remove(edge)
                            if edge.scene():
                                edge.scene().removeItem(edge)

                # Composite output port → external node
                elif edge.start_node is comp_item:
                    src_anchor = getattr(edge, "_source_anchor", None)
                    port_name = getattr(src_anchor, "port_name", "")
                    internal_name = self._find_internal_by_port(comp_id, port_name, "output")
                    if internal_name:
                        internal_item = self._canvas.nodes.get(internal_name)
                        if internal_item:
                            new_edge = EdgeItem(
                                internal_item,
                                edge.end_node,
                                self._canvas,
                                target_anchor=getattr(edge, "_target_anchor", None),
                                source_anchor=internal_item.output_anchor,
                            )
                            if hasattr(edge, "_waypoints") and edge._waypoints:
                                new_edge._waypoints = list(edge._waypoints)
                            self._canvas.scene.addItem(new_edge)
                            self._canvas.edges.append(new_edge)
                            new_edge.update_path()
                            # Remove old ghost edge
                            if edge in self._canvas.edges:
                                self._canvas.edges.remove(edge)
                            if edge.scene():
                                edge.scene().removeItem(edge)

        # 移除复合节点
        if comp_item:
            self._canvas.nodes.pop(comp_id, None)
            self._canvas.scene.removeItem(comp_item)

        # 还原原始节点位置
        for n in node_names:
            item = self._canvas.nodes.get(n)
            if item:
                pos = positions.get(n, {})
                item.setPos(QPointF(pos.get("x", 0), pos.get("y", 0)))
                item.setVisible(True)

        # Restore internal edges (hidden during compression)
        for info in comp.get("_internal_edges", []):
            for edge in self._canvas.edges:
                src_name = edge.start_node.node_name if hasattr(edge.start_node, "node_name") else ""
                tgt_name = edge.end_node.node_name if hasattr(edge.end_node, "node_name") else ""
                if src_name == info["src"] and tgt_name == info["tgt"]:
                    edge.setVisible(True)
                    break
        # Restore external edges (hidden during compression)
        for info in comp.get("_external_edges", []):
            for edge in self._canvas.edges:
                src_name = edge.start_node.node_name if hasattr(edge.start_node, "node_name") else ""
                tgt_name = edge.end_node.node_name if hasattr(edge.end_node, "node_name") else ""
                if src_name == info["src"] and tgt_name == info["tgt"]:
                    edge.setVisible(True)
                    break


# ── Background worker for compress I/O ──


class _CompressWorker(QThread):
    """Runs merge_requirements in a background thread to avoid UI freeze."""

    def __init__(
        self, project_path: str, comp_id: str, display_name: str, node_names: list, nodes_data: dict, parent=None
    ):
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

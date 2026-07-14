"""画布渲染门 Mixin —— Canonical 扫描调度 + 幽灵边打标 + 手动校准 Action。

把反向闭环（配置 → UI）的 3 大触发点封装成单个 Mixin（挂到 CanvasConnections 同层的 Canvas 对象上）：
1. 定时触发：3s 扫描（失活暂停 / 激活后延迟执行，避免空转 IO）
2. 手动触发：Action「校准线条」action_calibrate_edges（画布菜单 / 工具栏按钮可直接连）
3. 加载触发：load_layout 后外部显式调用 `schedule_immediate_scan`（由 canvas.load_layout 插入）

扫描流程：
    CanonicalEdgeResolver.infer_all_edges()
          ↓ set[EdgeKey]
    对 scene 中每个 EdgeItem：
          edge.set_render_gate_valid(edge._edge_key ∈ canonical_set)
          if not valid: logger [EDGE-GHOST DETECTED] ...
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QAction

from ui.core.edge.canonical_edge_resolver import (
    CanonicalEdgeResolver,
    get_global_mtime_cache,
)
from ui.core.logger import logger
from ui.core.state.node_state_manager import NodeStateManager


class CanvasEdgeRenderGateMixin(QObject):
    """挂到 Canvas 上的渲染门调度 mixin（与 CanvasConnections 平级）。"""

    # 参数
    CANONICAL_SCAN_INTERVAL_MS = 10_000  # 稳态 10s 兜底扫一次（expand/collapse/load_layout/calibrate 都会立即 schedule_immediate_scan，不依赖定时器）
    PAUSE_ON_INACTIVE = True
    RESUME_DELAY_MS = 1500  # 激活后延迟一下，避免反复 focus 抖动导致密集扫

    def __init__(self, canvas: Any, parent=None) -> None:
        super().__init__(parent or canvas)
        self.canvas = canvas
        self._resolver = CanonicalEdgeResolver()
        self._last_canonical_set: set | None = None
        self._last_canvas_edge_keys_fprint: tuple | None = None
        self._scan_in_progress = False

        # 定时器
        self._scan_timer = QTimer(self)
        self._scan_timer.setInterval(self.CANONICAL_SCAN_INTERVAL_MS)
        self._scan_timer.timeout.connect(self._on_scan_timer)
        self._start_if_app()

        # 应用级激活/失活检测：windowActiveChanged（单例 QGuiApplication）
        self._app_state_observer_installed = False
        self._install_app_state_observer()

    # ───────── public 入口：外部调用 ─────────

    def schedule_immediate_scan(self, purge_stale: bool = False) -> None:
        """立即触发一次 Canonical 扫描（load_layout 后、add_node 后、expand/collapse morph 后都可以调）。"""
        self._run_scan(purge_stale=purge_stale)

    def last_canonical_set(self) -> set | None:
        """返回上一次扫描得到的 CanonicalEdgeSet（测试用 / 外部 debug 用）。"""
        return self._last_canonical_set

    def action_calibrate_edges(self) -> QAction:
        """返回可挂到菜单/工具栏的 QAction：手动触发校准线条 + 清理过期路由。"""
        act = QAction("校准线条", self.canvas)
        act.setToolTip("强制从所有 node_config.json / composite.json 重新推导线条，清理无效配置")
        act.triggered.connect(self._on_action_calibrate)
        return act

    # ───────── 内部：调度器 ─────────

    def _start_if_app(self) -> None:
        try:
            from PySide6.QtWidgets import QApplication

            if QApplication.instance() is not None:
                self._scan_timer.start()
        except Exception:  # noqa: BLE001
            # 测试环境无 QApp，不启动
            pass

    def _install_app_state_observer(self) -> None:
        if self._app_state_observer_installed:
            return
        try:
            from PySide6.QtGui import QGuiApplication

            app = QGuiApplication.instance()
            if app is None:
                return
            # focusWindowChanged 足够表达失活/激活：所有窗口都失焦 → focusWindow == None
            app.focusWindowChanged.connect(self._on_focus_window_changed)
            self._app_state_observer_installed = True
        except Exception as e:  # noqa: BLE001
            logger.debug("[CANONICAL] app state observer unavailable: %s", e)

    def _on_focus_window_changed(self, _win: Any) -> None:
        if not self.PAUSE_ON_INACTIVE:
            return
        try:
            from PySide6.QtGui import QGuiApplication

            app = QGuiApplication.instance()
            if app is None:
                return
            focused = app.focusWindow()
            if focused is None:
                if self._scan_timer.isActive():
                    self._scan_timer.stop()
                    logger.debug("[CANONICAL] scheduler paused: no focused window")
            else:
                if not self._scan_timer.isActive():
                    # 激活后延迟扫描，避免频繁切换抖动
                    QTimer.singleShot(self.RESUME_DELAY_MS, self._start_after_resume)
        except Exception as e:  # noqa: BLE001
            logger.debug("[CANONICAL] focusWindow hook fail: %s", e)

    def _start_after_resume(self) -> None:
        try:
            from PySide6.QtGui import QGuiApplication

            app = QGuiApplication.instance()
            if app is None:
                return
            # 再次确认：如果在 RESUME_DELAY_MS 期间又失活了，就不启动
            if app.focusWindow() is None:
                return
        except Exception:
            pass
        if not self._scan_timer.isActive():
            self._scan_timer.start()
            logger.debug("[CANONICAL] scheduler resumed (after %dms delay)", self.RESUME_DELAY_MS)
        # 激活后马上跑一次补偿扫描
        QTimer.singleShot(0, lambda: self._run_scan(purge_stale=False))

    def _on_scan_timer(self) -> None:
        # 画布还没加载项目时别扫
        if not self._has_project():
            return
        self._run_scan(purge_stale=False)

    def _on_action_calibrate(self) -> None:
        logger.info("[CANONICAL] manual calibrate action triggered")
        get_global_mtime_cache().clear()  # 手动校准时忽略缓存，强制全量重读
        self._run_scan(purge_stale=True)

    # ───────── 核心扫描 + 渲染门打标 ─────────

    def _has_project(self) -> bool:
        c = self.canvas
        return bool(getattr(c, "project_path", None))

    def _run_scan(self, purge_stale: bool) -> None:
        if self._scan_in_progress:
            return
        if not self._has_project():
            return
        self._scan_in_progress = True
        try:
            self._do_scan_and_apply(purge_stale=purge_stale)
        except Exception as e:  # noqa: BLE001
            logger.exception("[CANONICAL] scan failed: %s", e)
        finally:
            self._scan_in_progress = False

    def _do_scan_and_apply(self, purge_stale: bool) -> None:
        c = self.canvas
        project_path = c.project_path
        nodes_data = {}
        composite_manager = getattr(c, "composite_manager", None)
        pw = getattr(c, "parent_window", None)
        if pw is not None:
            nodes_data = getattr(pw, "nodes_data", {}) or {}

        # (1) 跑权威反向推断 — 在赋值前保存旧集，比较是否变化
        old_canonical_set = self._last_canonical_set
        canonical_set, stats = self._resolver.infer_all_edges(
            project_path=project_path,
            nodes_data=nodes_data,
            composite_manager=composite_manager,
        )
        self._last_canonical_set = canonical_set

        # (2) 清理过期路由（manual 校准才开）
        if purge_stale:
            cleared = self._resolver.purge_stale_routes(
                project_path=project_path,
                nodes_data=nodes_data,
                composite_manager=composite_manager,
                dry_run=False,
            )
            logger.info("[CANONICAL] purge_stale_routes cleared=%d", cleared)

        # (3) 遍历画布上所有 EdgeItem，逐个走渲染门
        ghost_count = 0
        scene = getattr(c, "scene", None)
        if callable(scene):
            scene = scene()
        items = []
        if scene is not None:
            items = list(scene.items())
        canvas_edge_entries: list[tuple[Any, str | None, str | None, str | None, str | None, bool]] = []
        for it in items:
            edge_key = getattr(it, "_edge_key", None)
            if edge_key is None:
                continue
            valid = NodeStateManager.is_edge_valid_static(edge_key, canonical_set)
            if not valid:
                ghost_count += 1
                logger.warning(
                    "[EDGE-GHOST DETECTED] %s | source=%s target=%s",
                    edge_key,
                    getattr(it.start_node, "node_name", None) if getattr(it, "start_node", None) else None,
                    getattr(it.end_node, "node_name", None) if getattr(it, "end_node", None) else None,
                )
            it.set_render_gate_valid(valid)
            sn = getattr(it.start_node, "node_name", None) if getattr(it, "start_node", None) else None
            tn = getattr(it.end_node, "node_name", None) if getattr(it, "end_node", None) else None
            sa = getattr(it, "start_anchor", None)
            ea = getattr(it, "end_anchor", None)
            sp = getattr(sa, "port_name", None) if sa else None
            ep = getattr(ea, "port_name", None) if ea else None
            canvas_edge_entries.append((edge_key, sn, sp, tn, ep, valid))

        canvas_fprint = (
            tuple(sorted((k, sn, sp, tn, ep, match) for (k, sn, sp, tn, ep, match) in canvas_edge_entries))
            if canvas_edge_entries
            else ()
        )
        old_canvas_fprint = self._last_canvas_edge_keys_fprint
        self._last_canvas_edge_keys_fprint = canvas_fprint
        canonical_changed = old_canonical_set != canonical_set
        canvas_changed = old_canvas_fprint != canvas_fprint
        noisy = purge_stale or canonical_changed or canvas_changed or (ghost_count > 0) or bool(stats.broken_paths)

        summary_log = logger.info if noisy else logger.debug
        summary_log(
            "[CANONICAL] render-gate applied: total_canonical=%d canvas_edges_checked=%d ghost=%d",
            len(canonical_set),
            len(canvas_edge_entries),
            ghost_count,
        )
        # 只在 noisy（内容变化 / 手动校准 / 有幽灵边）时才上 INFO 做完整 dump；
        # 稳态闲置时降到 DEBUG，避免 3s 一次刷屏（但用户想排查仍可把 logger 切到 DEBUG）
        dump_log = logger.info if noisy else logger.debug
        dump_log("[CANONICAL] === Canonical set dump (len=%d) ===", len(canonical_set))
        for k in sorted(canonical_set, key=lambda x: (x[0], x[1], x[2], x[3], x[4])):
            dump_log("  CANON: %s", k)
        dump_log("[CANONICAL] === Canvas EdgeItem._edge_key dump ===")
        for ek, sn, sp, tn, ep, match in canvas_edge_entries:
            dump_log("  CANVAS: %s | start=%s[%s] end=%s[%s] | valid=%s", ek, sn, sp, tn, ep, match)

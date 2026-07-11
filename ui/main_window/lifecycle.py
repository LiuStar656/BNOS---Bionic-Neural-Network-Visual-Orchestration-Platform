"""
BNOS Main Window Lifecycle Management Mixin

Handles startup and shutdown orchestration:
- Initialization flow
- Shutdown flow
- Event handling (show, close, resize, etc.)
"""

from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow

from ui.core.logger import logger


class MainWindowLifecycleMixin:
    """
    Main window lifecycle management Mixin

    Provides orchestration logic for window startup and shutdown,
    used in conjunction with BNOSMainWindow.
    """

    def _init_and_restore(self):
        """[Core] Init and restore flow: create panels first, then restore layout.

        Following VSCode's approach:
        1. Create all needed views/panels
        2. Then restore layout state (including splitter positions)
        """
        logger.info("Entering _init_and_restore()")

        # ===== Step 1: Create panels first (ensure Docks exist) =====
        logger.info("Step 1: Create panels")
        self._restore_panel_state()

        # ===== Step 2: Deferred window state restore =====
        # Give Qt a moment for Docks to finish creating
        QTimer.singleShot(200, lambda: self._restore_window_state_with_docks())

        # ===== Step 3: Auto-open last project =====
        QTimer.singleShot(800, self.auto_open_last_project)

        logger.info("Leaving _init_and_restore()")

    def _restore_window_state_with_docks(self):
        """Restore window state after Docks are created."""
        logger.info("Entering _restore_window_state_with_docks()")

        # At this point Docks are created, safe to call restoreState()
        self.restore_window_state()

        logger.info("Leaving _restore_window_state_with_docks()")

    def showEvent(self, event):
        """Window show event."""
        super().showEvent(event)
        logger.info("Main window shown")

    def closeEvent(self, event):
        """Window close event, save all state."""
        logger.info("Starting close check...")
        logger.info("   Current project: %s", self.current_project_path)
        logger.info("   Total nodes: %d", len(self.nodes_data))

        # Immediately set closing flag to prevent subsequent hideEvent from overwriting persisted state
        if hasattr(self, "_canvas_host") and self._canvas_host:
            self._canvas_host._is_closing = True
            if hasattr(self._canvas_host, "_terminal_dock") and self._canvas_host._terminal_dock:
                self._canvas_host._terminal_dock._is_closing = True
                logger.info("Set TerminalDock._is_closing = True")

        # Wait for node creation thread to finish (if running)
        if hasattr(self, "node_creation_worker"):
            try:
                if self.node_creation_worker and self.node_creation_worker.isRunning():
                    logger.info("Waiting for node creation thread...")
                    self.node_creation_worker.wait(5000)
                    if self.node_creation_worker.isRunning():
                        logger.warning("Node creation thread timeout, force terminating")
                        self.node_creation_worker.terminate()
            except RuntimeError:
                logger.info("Node creation thread object already cleaned up")

        # Wait for node start threads to finish
        if hasattr(self, "_node_start_workers") and self._node_start_workers:
            logger.info("Waiting for %d node start threads...", len(self._node_start_workers))
            for worker in list(self._node_start_workers):
                if worker.isRunning():
                    worker.wait(3000)
                    if worker.isRunning():
                        logger.warning("Node start thread timeout, force terminating")
                        worker.terminate()

        # Wait for node stop threads to finish
        if hasattr(self, "_stop_node_workers") and self._stop_node_workers:
            logger.info("Waiting for %d node stop threads...", len(self._stop_node_workers))
            for worker in list(self._stop_node_workers):
                if worker.isRunning():
                    worker.wait(3000)
                    if worker.isRunning():
                        logger.warning("Node stop thread timeout, force terminating")
                        worker.terminate()

        # Check for running nodes
        running_nodes = []
        for node_name, node_info in self.nodes_data.items():
            status = node_info.get("status", "unknown")
            process = node_info.get("process", None)
            logger.debug("Node %s: status=%s, process=%s", node_name, status, "exists" if process else "None")

            if status == "running" and process:
                running_nodes.append(node_name)

        logger.info("Detected %d running nodes: %s", len(running_nodes), running_nodes)

        # Prompt user if there are running nodes
        if running_nodes:
            nodes_list = "\n".join([f"  - {name}" for name in running_nodes[:10]])
            if len(running_nodes) > 10:
                nodes_list += f"\n... and {len(running_nodes) - 10} more nodes"

            from ui.core.i18n import t
            from ui.core.utils.dialog_utils import MSG_ACCEPT, MSG_REJECT, themed_message

            reply = themed_message(
                self,
                t("k_title_detect_running"),
                t("_k_close_running_nodes").format(count=len(running_nodes), nodes=nodes_list),
                "question3",
            )

            if reply == MSG_ACCEPT:
                logger.info("Closing %d running nodes...", len(running_nodes))
                self._force_stop_all_nodes(running_nodes)
                self.show_toast(t("_k_nodes_closed").format(count=len(running_nodes)), "success")
            elif reply == MSG_REJECT:
                logger.info("%d nodes will continue running in background", len(running_nodes))
                self.show_toast(t("_k_nodes_background").format(count=len(running_nodes)), "info")
                # Continue with save and close logic
            else:
                logger.info("User cancelled close operation")
                # Reset closing flag
                if hasattr(self, "_canvas_host") and self._canvas_host:
                    self._canvas_host._is_closing = False
                    if hasattr(self._canvas_host, "_terminal_dock") and self._canvas_host._terminal_dock:
                        self._canvas_host._terminal_dock._is_closing = False
                event.ignore()
                return

        # Run save + stop flow via ShutdownOrchestrator
        logger.info("[SHUTDOWN] === Starting shutdown orchestrator ===")
        try:
            self._shutdown_orchestrator.execute()
        except Exception as e:
            logger.error("Shutdown orchestrator failed: %s", e)

        # ── Cleanup chain: clean panel threads/timers ──
        self._cleanup_on_shutdown()

        logger.info("Window close flow complete, all data safely saved")
        event.accept()

    def _cleanup_on_shutdown(self):
        """Cleanup chain on window close (release threads, timers, monitors, callbacks)."""
        logger.info("[CLEANUP] Starting shutdown cleanup chain...")

        # 1. Disconnect all NodeItem signal connections and child objects on canvas
        if self.canvas:
            canvas = self.canvas
            try:
                all_items = canvas.items() if hasattr(canvas, "items") else []
                for item in all_items:
                    if hasattr(item, "dispose"):
                        try:
                            item.dispose()
                        except Exception as e:
                            logger.debug("dispose node_item error: %s", e)
                logger.debug("[CLEANUP] NodeItem signals disconnected")
            except Exception as e:
                logger.warning("[CLEANUP] NodeItem cleanup error: %s", e)

        # 2. Clear PollingManager node-level watchers and stop worker thread
        try:
            from ui.core.system.polling_manager import polling_manager

            polling_manager.cleanup_all_watchers()
            if hasattr(polling_manager, "_worker_thread") and polling_manager._worker_thread:
                polling_manager._worker_thread.quit()
                polling_manager._worker_thread.wait(2000)
                if polling_manager._worker_thread.isRunning():
                    polling_manager._worker_thread.terminate()
                    polling_manager._worker_thread.wait(1000)
            logger.debug("[CLEANUP] PollingManager watchers and worker thread cleared")
        except Exception as e:
            logger.warning("[CLEANUP] Monitor cleanup error: %s", e)

        # 3. Stop NodeControlService callbacks and cleanup all monitor threads
        try:
            from ui.core.node.node_control_service import node_control_service

            node_control_service._status_callbacks.clear()
            node_control_service.cleanup_all_monitors()
            logger.debug("[CLEANUP] NodeControlService callbacks + monitor threads cleared")
        except Exception as e:
            logger.warning("[CLEANUP] NodeControlService cleanup error: %s", e)

        # 4. Stop startup queue worker thread
        try:
            from ui.core.node.node_startup_queue import startup_queue

            if hasattr(startup_queue, "stop_queue"):
                startup_queue.stop_queue()
            logger.debug("[CLEANUP] Startup queue stopped")
        except Exception as e:
            logger.warning("[CLEANUP] Startup queue cleanup error: %s", e)

        # 5. Stop all timers and background threads in Dock panels
        try:
            from ui.core.dock.dock_manager import DockManager

            titles = list(self._dock_manager.get_all_dock_titles())
            for dock_title in titles:
                dock = self._dock_manager.get_dock_by_title(dock_title)
                if not dock:
                    continue
                try:
                    DockManager._stop_content_timers(dock)
                    content = dock.get_content_widget()
                    if content and hasattr(content, "dispose"):
                        try:
                            content.dispose()
                            logger.debug("[CLEANUP] Panel disposed: %s", dock_title)
                        except RuntimeError:
                            pass
                except RuntimeError:
                    pass
            logger.debug("[CLEANUP] Panel timers and threads stopped")
        except Exception as e:
            logger.warning("[CLEANUP] Panel timer cleanup error: %s", e)

        # 6. Close global thread pool
        try:
            from ui.core.system.thread_pool import thread_pool

            thread_pool.shutdown()
            logger.debug("[CLEANUP] Global thread pool closed")
        except Exception as e:
            logger.warning("[CLEANUP] Thread pool close error: %s", e)

        logger.info("[CLEANUP] Cleanup chain complete")

    def _shutdown_save_all_data(self):
        """Save all data (layout/window state/panel visibility/floating panel positions)."""
        logger.info("[SHUTDOWN] === Starting save all data ===")

        if hasattr(self, "_canvas_host") and self._canvas_host:
            self._canvas_host.update_canvas_data_from_main_window(self.canvas)

        if self.current_project_path and hasattr(self, "_canvas_host"):
            self._canvas_host.save_all_layouts(self.current_project_path)

        logger.info("[SAVE] Saving window state...")
        self.save_window_state()
        self.app_config.set("last_project", self.current_project_path)

        logger.info("[SAVE] Saving panel visibility...")
        self._save_panel_visibility()

        logger.info("[SAVE] Force saving config to file...")
        self.app_config.save()

        import os

        if os.path.exists(self.app_config.config_file):
            logger.info("Config file saved successfully: %s", self.app_config.config_file)
        else:
            logger.error("Config file save failed, file does not exist")

        logger.info("[SHUTDOWN] === All data saved ===")

    def moveEvent(self, event):
        """Window move event."""
        QMainWindow.moveEvent(self, event)

        if self.CANVAS_PROCESS_MODE:
            self._sync_canvas_geometry()

        if hasattr(self, "node_monitor") and self.node_monitor is not None and self.node_monitor.isVisible():
            p = self.pos()
            monitor_x = p.x() + self.width() - 440
            monitor_y = p.y() + 40
            self.node_monitor.move(monitor_x, monitor_y)

        if hasattr(self, "toast_manager"):
            self.toast_manager._update_positions()

    def resizeEvent(self, event):
        """Window resize event."""
        QMainWindow.resizeEvent(self, event)

        if self.CANVAS_PROCESS_MODE:
            self._sync_canvas_geometry()

        if hasattr(self, "node_monitor") and self.node_monitor is not None and self.node_monitor.isVisible():
            p = self.pos()
            monitor_x = p.x() + self.width() - 440
            monitor_y = p.y() + 40
            self.node_monitor.move(monitor_x, monitor_y)

        if hasattr(self, "toast_manager"):
            self.toast_manager._update_positions()

    def _sync_canvas_geometry(self):
        """Sync canvas process geometry info."""
        if not self.CANVAS_PROCESS_MODE:
            return

        try:
            from ui.core.system.ipc import send_canvas_geometry

            send_canvas_geometry(self)
        except Exception as e:
            logger.error("Failed to sync canvas geometry: %s", e)

    def _stop_terminal_subprocesses(self):
        """Stop all subprocesses in terminal."""
        if hasattr(self, "_canvas_host") and self._canvas_host:
            ch = self._canvas_host
            if hasattr(ch, "_terminal_dock") and ch._terminal_dock:
                logger.info("Stopping terminal processes...")
                ch._terminal_dock.stop_all_terminals()

    def _force_stop_all_nodes(self, node_names):
        """Force stop all specified node processes."""
        from ui.core.node.node_process import stop_node_process

        for node_name in node_names:
            if node_name in self.nodes_data:
                stop_node_process(self.nodes_data[node_name])
                logger.info("Node %s stopped", node_name)

        if hasattr(self, "node_list_panel") and self.node_list_panel:
            self.node_list_panel.update_node_list(self.nodes_data)

        if self.canvas:
            self.canvas.sync_all_nodes_display()

    def _disconnect_terminal_signals(self):
        """Disconnect terminal signal connections."""
        if hasattr(self, "_canvas_host") and self._canvas_host:
            ch = self._canvas_host
            if hasattr(ch, "_terminal_dock") and ch._terminal_dock:
                logger.info("Disconnecting TerminalDock visibility_changed signal...")
                try:
                    ch._terminal_dock.visibility_changed.disconnect()
                    logger.info("Terminal signals disconnected")
                except Exception as e:
                    logger.warning("Signal disconnect failed: %s", e)

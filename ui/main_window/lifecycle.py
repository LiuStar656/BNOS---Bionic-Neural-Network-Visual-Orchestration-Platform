"""
BNOS 主窗口生命周期管理模块

负责主窗口的启动和关闭流程编排，包括：
- 初始化流程
- 关闭流程
- 事件处理（显示、关闭、调整大小等）
"""
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow
from ui.core.logger import logger


class MainWindowLifecycleMixin:
    """
    主窗口生命周期管理 Mixin
    
    提供窗口启动和关闭的编排逻辑，需要与 BNOSMainWindow 配合使用。
    """
    
    def _init_and_restore(self):
        """【核心】初始化和恢复流程：先创建面板，再恢复布局
        
        参考 VSCode 的做法：
        1. 先创建所有需要的视图/面板
        2. 然后恢复布局状态（包括分割条位置）
        """
        logger.info("进入 _init_and_restore()")
        
        # ===== 步骤 1：先创建面板（确保 Dock 存在） =====
        logger.info("步骤 1：先创建面板")
        self._restore_panel_state()
        
        # ===== 步骤 2：延迟恢复窗口状态（Qt 状态和尺寸） =====
        # 给 Qt 一点时间让 Dock 创建完成
        QTimer.singleShot(200, lambda: self._restore_window_state_with_docks())
        
        # ===== 步骤 3：自动打开上次项目 =====
        QTimer.singleShot(800, self.auto_open_last_project)
        
        logger.info("离开 _init_and_restore()")
    
    def _restore_window_state_with_docks(self):
        """Dock 创建完成后，恢复窗口状态"""
        logger.info("进入 _restore_window_state_with_docks()")
        
        # 此时 Dock 已经创建好了，可以安全调用 restoreState()
        self.restore_window_state()
        
        logger.info("离开 _restore_window_state_with_docks()")
    
    def showEvent(self, event):
        """窗口显示事件"""
        super().showEvent(event)
        logger.info("主窗口显示")
    
    def closeEvent(self, event):
        """窗口关闭事件，保存所有状态"""
        logger.info("开始关闭窗口检测...")
        logger.info("   当前项目: %s", self.current_project_path)
        logger.info("   节点总数: %d", len(self.nodes_data))
        
        # 立即设置关闭标志，防止后续 hideEvent 覆盖持久化状态
        if hasattr(self, '_canvas_host') and self._canvas_host:
            self._canvas_host._is_closing = True
            # 同时设置 TerminalDock 的关闭标志
            if hasattr(self._canvas_host, '_terminal_dock') and self._canvas_host._terminal_dock:
                self._canvas_host._terminal_dock._is_closing = True
                logger.info("🔒 设置 TerminalDock._is_closing = True")
        
        # 等待节点创建线程完成（如果正在运行）
        if hasattr(self, 'node_creation_worker'):
            try:
                # 检查对象是否仍然有效（未被deleteLater删除）
                if self.node_creation_worker and self.node_creation_worker.isRunning():
                    logger.info("等待节点创建线程完成...")
                    self.node_creation_worker.wait(5000)
                    if self.node_creation_worker.isRunning():
                        logger.warning("节点创建线程超时，强制终止")
                        self.node_creation_worker.terminate()
            except RuntimeError:
                # 对象已被删除
                logger.info("节点创建线程对象已被清理")
        
        # 等待节点启动线程完成
        if hasattr(self, '_node_start_workers') and self._node_start_workers:
            logger.info("等待 %d 个节点启动线程完成...", len(self._node_start_workers))
            for worker in list(self._node_start_workers):
                if worker.isRunning():
                    worker.wait(3000)
                    if worker.isRunning():
                        logger.warning("节点启动线程超时，强制终止")
                        worker.terminate()

        # 等待节点停止线程完成
        if hasattr(self, '_stop_node_workers') and self._stop_node_workers:
            logger.info("等待 %d 个节点停止线程完成...", len(self._stop_node_workers))
            for worker in list(self._stop_node_workers):
                if worker.isRunning():
                    worker.wait(3000)
                    if worker.isRunning():
                        logger.warning("节点停止线程超时，强制终止")
                        worker.terminate()
        
        # 检查是否有运行中的节点
        running_nodes = []
        for node_name, node_info in self.nodes_data.items():
            status = node_info.get('status', 'unknown')
            process = node_info.get('process', None)
            logger.debug("节点 %s: status=%s, process=%s", node_name, status, '存在' if process else 'None')
            
            if status == 'running' and process:
                running_nodes.append(node_name)
        
        logger.info("检测到 %d 个运行中的节点: %s", len(running_nodes), running_nodes)
        
        # 如果有运行中的节点，提示用户
        if running_nodes:
            nodes_list = "\n".join([f"• {name}" for name in running_nodes[:10]])  # 最多显示10个
            if len(running_nodes) > 10:
                nodes_list += f"\n... 还有 {len(running_nodes) - 10} 个节点"
            
            from ui.core.utils.dialog_utils import MSG_ACCEPT, MSG_REJECT, MSG_CANCEL, themed_message
            from ui.core.i18n import t
            reply = themed_message(
                self, t("k_title_detect_running"),
                t("_k_close_running_nodes").format(count=len(running_nodes), nodes=nodes_list),
                "question3"
            )
            
            if reply == MSG_ACCEPT:
                logger.info("正在关闭 %d 个运行中的节点...", len(running_nodes))
                self._force_stop_all_nodes(running_nodes)
                self.show_toast(t("_k_nodes_closed").format(count=len(running_nodes)), "success")
            elif reply == MSG_REJECT:
                # 用户选择不关闭，让进程继续运行
                logger.info("%d 个节点将继续在后台运行", len(running_nodes))
                self.show_toast(t("_k_nodes_background").format(count=len(running_nodes)), "info")
                # 继续执行后续的保存和关闭逻辑
            else:
                # 用户选择取消，中止关闭操作
                logger.info("用户取消了关闭操作")
                event.ignore()  # 忽略关闭事件，保持窗口打开
                return
        
        # 通过 ShutdownOrchestrator 执行保存+停止流程
        logger.info("[SHUTDOWN] === 启动关闭编排器 ===")
        try:
            self._shutdown_orchestrator.execute()
        except Exception as e:
            logger.error("关闭编排器执行失败: %s", e)

        # ── 清理链：防止信号/内存泄漏 ──
        self._cleanup_on_shutdown()

        logger.info("✅ 窗口关闭流程完成，所有数据已安全保存")
        event.accept()

    def _cleanup_on_shutdown(self):
        """窗口关闭时的清理链（释放线程、定时器、监控器、回调等）"""
        logger.info("[CLEANUP] 开始关闭清理链...")

        # 1. 释放画布上所有 NodeItem 的信号连接和子对象
        if self.canvas:
            canvas = self.canvas
            try:
                all_items = canvas.items() if hasattr(canvas, 'items') else []
                for item in all_items:
                    if hasattr(item, 'dispose'):
                        try:
                            item.dispose()
                        except Exception as e:
                            logger.debug("dispose node_item 异常: %s", e)
                logger.debug("[CLEANUP] NodeItem 信号已断开")
            except Exception as e:
                logger.warning("[CLEANUP] NodeItem 清理异常: %s", e)

        # 2. 清空 PollingManager 节点级监控器并停止工作线程
        try:
            from ui.core.polling_manager import polling_manager
            polling_manager.cleanup_all_watchers()
            if hasattr(polling_manager, '_worker_thread') and polling_manager._worker_thread:
                polling_manager._worker_thread.quit()
                polling_manager._worker_thread.wait(2000)
                if polling_manager._worker_thread.isRunning():
                    polling_manager._worker_thread.terminate()
                    polling_manager._worker_thread.wait(1000)
            logger.debug("[CLEANUP] PollingManager 监控器+工作线程已清理")
        except Exception as e:
            logger.warning("[CLEANUP] 监控器清理异常: %s", e)

        # 3. 停止 NodeControlService 回调并清理所有监控线程
        try:
            from ui.core.node_control_service import node_control_service
            node_control_service._status_callbacks.clear()
            node_control_service.cleanup_all_monitors()
            logger.debug("[CLEANUP] NodeControlService 回调+监控线程已清理")
        except Exception as e:
            logger.warning("[CLEANUP] NodeControlService 清理异常: %s", e)

        # 4. 停止启动队列的工作线程
        try:
            from ui.core.node_startup_queue import startup_queue
            if hasattr(startup_queue, 'stop_queue'):
                startup_queue.stop_queue()
            logger.debug("[CLEANUP] 启动队列已停止")
        except Exception as e:
            logger.warning("[CLEANUP] 启动队列清理异常: %s", e)

        # 5. 停止所有Dock面板中的定时器，防止线程残留
        try:
            from PySide6.QtCore import QTimer
            from PySide6.QtCore import QThread
            count_timers = 0
            count_threads = 0
            for dock_title in list(self._dock_manager.get_all_dock_titles()):
                dock = self._dock_manager.get_dock_by_title(dock_title)
                if dock:
                    content = dock.get_content_widget()
                    if content:
                        for child in content.findChildren(QTimer):
                            try:
                                if child.isActive():
                                    child.stop()
                                    count_timers += 1
                            except RuntimeError:
                                pass
            logger.debug("[CLEANUP] 面板 %d 个定时器已停止", count_timers)
        except Exception as e:
            logger.warning("[CLEANUP] 面板定时器清理异常: %s", e)

        logger.info("[CLEANUP] 清理链完成")
    
    def _shutdown_save_all_data(self):
        """保存所有数据（布局/窗口状态/面板可见性/浮动面板位置）"""
        logger.info("[SHUTDOWN] === 开始保存所有数据 ===")
        
        if hasattr(self, '_canvas_host') and self._canvas_host:
            self._canvas_host.update_canvas_data_from_main_window(self.canvas)
        
        if self.current_project_path and hasattr(self, '_canvas_host'):
            self._canvas_host.save_all_layouts(self.current_project_path)
        
        logger.info("[SAVE] 保存窗口状态...")
        self.save_window_state()
        self.app_config.set("last_project", self.current_project_path)
        
        logger.info("[SAVE] 保存面板可见性...")
        self._save_panel_visibility()
        
        logger.info("[SAVE] 强制保存配置到文件...")
        self.app_config.save()
        
        import os
        if os.path.exists(self.app_config.config_file):
            logger.info("配置文件保存成功: %s", self.app_config.config_file)
        else:
            logger.error("配置文件保存失败，文件不存在")
        
        logger.info("[SHUTDOWN] === 所有数据保存完成 ===")
    
    def moveEvent(self, event):
        """窗口移动事件"""
        QMainWindow.moveEvent(self, event)
        
        if self.CANVAS_PROCESS_MODE:
            self._sync_canvas_geometry()
        
        # 浮动的节点监测面板跟随主窗口移动
        if hasattr(self, 'node_monitor') and self.node_monitor is not None and self.node_monitor.isVisible():
            p = self.pos()
            monitor_x = p.x() + self.width() - 440
            monitor_y = p.y() + 40
            self.node_monitor.move(monitor_x, monitor_y)
        
        if hasattr(self, 'toast_manager'):
            self.toast_manager._update_positions()
    
    def resizeEvent(self, event):
        """窗口大小改变事件"""
        QMainWindow.resizeEvent(self, event)
        
        if self.CANVAS_PROCESS_MODE:
            self._sync_canvas_geometry()
        
        # 浮动的节点监测面板跟随主窗口调整位置
        if hasattr(self, 'node_monitor') and self.node_monitor is not None and self.node_monitor.isVisible():
            p = self.pos()
            monitor_x = p.x() + self.width() - 440
            monitor_y = p.y() + 40
            self.node_monitor.move(monitor_x, monitor_y)
        
        if hasattr(self, 'toast_manager'):
            self.toast_manager._update_positions()
    
    def _sync_canvas_geometry(self):
        """同步画布进程的几何信息"""
        if not self.CANVAS_PROCESS_MODE:
            return
        
        try:
            from ui.core.ipc import send_canvas_geometry
            send_canvas_geometry(self)
        except Exception as e:
            logger.error("同步画布几何信息失败: %s", e)
    
    def _stop_terminal_subprocesses(self):
        """停止终端中的所有子进程"""
        if hasattr(self, '_canvas_host') and self._canvas_host:
            ch = self._canvas_host
            if hasattr(ch, '_terminal_dock') and ch._terminal_dock:
                logger.info("停止终端进程...")
                ch._terminal_dock.stop_all_terminals()
    
    def _force_stop_all_nodes(self, node_names):
        """强制停止所有指定节点进程"""
        from ui.core.node_process import stop_node_process
        
        for node_name in node_names:
            if node_name in self.nodes_data:
                stop_node_process(self.nodes_data[node_name])
                logger.info("节点 %s 已停止", node_name)
        
        if hasattr(self, 'node_list_panel') and self.node_list_panel:
            self.node_list_panel.update_node_list(self.nodes_data)
        
        if self.canvas:
            self.canvas.sync_all_nodes_display()
    
    def _disconnect_terminal_signals(self):
        """断开终端信号连接"""
        if hasattr(self, '_canvas_host') and self._canvas_host:
            ch = self._canvas_host
            if hasattr(ch, '_terminal_dock') and ch._terminal_dock:
                logger.info("断开终端 Dock 的 visibility_changed 信号...")
                try:
                    ch._terminal_dock.visibility_changed.disconnect()
                    logger.info("终端信号已断开")
                except Exception as e:
                    logger.warning("断开信号失败: %s", e)

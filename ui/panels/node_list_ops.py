"""
共享的节点列表操作 Mixin — 消除 node_list_dock.py 与 node_list_panel.py 中 ~400+ 行重复代码
从 node_list_dock.py 提取（使用更安全的 hasattr 检查），供两个面板共同继承
"""
import os
import subprocess
import time
from PySide6.QtWidgets import QTreeWidgetItem
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.utils.dialog_utils import themed_message
from ui.core.node_startup_queue import startup_queue


class NodeListOperationsMixin:
    """节点列表通用操作（适用于 Dock 和 Floating 版本）"""

    # ======================== 节点树操作方法 ========================

    def _setup_node_item(self, item, node_name, node_info):
        """配置节点项"""
        status = node_info.get('status', 'stopped')
        self._update_node_item_status(item, node_name, status)
        item.setData(0, Qt.ItemDataRole.UserRole, {'type': 'node', 'name': node_name})

    def update_node_status(self, node_name, status):
        """更新节点状态"""
        root = self.node_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('type') == 'node' and data.get('name') == node_name:
                self._update_node_item_status(item, node_name, status)
                return
            for j in range(item.childCount()):
                node_item = item.child(j)
                node_data = node_item.data(0, Qt.ItemDataRole.UserRole)
                if node_data and node_data.get('type') == 'node' and node_data.get('name') == node_name:
                    self._update_node_item_status(node_item, node_name, status)
                    return

    def _update_node_item_status(self, item, node_name, status):
        """更新单个节点项的状态显示"""
        if status in ('running', 'idle'):
            item.setText(0, f"● {node_name}")
            item.setForeground(0, QColor("green"))
        elif status == 'queued':
            item.setText(0, f"◎ {node_name}")
            item.setForeground(0, QColor("#4A90E2"))
        elif status == 'blocked':
            item.setText(0, f"⚠ {node_name}")
            item.setForeground(0, QColor("#F5A623"))
        elif status == 'starting':
            item.setText(0, f"◐ {node_name}")
            item.setForeground(0, QColor("#F5A623"))
        else:
            item.setText(0, f"○ {node_name}")
            item.setForeground(0, QColor("gray"))

    def _on_node_status_changed(self, node_name, new_status):
        """处理全局节点状态变化信号"""
        self.update_node_status(node_name, new_status)

    def get_selected_nodes(self):
        """获取所有选中的节点名称"""
        selected_items = self.node_tree.selectedItems()
        nodes = []
        for item in selected_items:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('type') == 'node':
                nodes.append(data['name'])
        return nodes

    def get_selected_groups(self):
        """获取所有选中的组名称"""
        selected_items = self.node_tree.selectedItems()
        groups = []
        for item in selected_items:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('type') == 'group':
                groups.append(data['name'])
        return groups

    def on_node_double_clicked(self, item, column):
        """节点双击事件 - 添加到画布"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get('type') != 'node':
            return
        node_name = data['name']
        if self.parent_window:
            if hasattr(self.parent_window, 'canvas') and self.parent_window.canvas and node_name in self.parent_window.canvas.nodes:
                self.parent_window.show_toast(t("_k_node_canvas_exists").format(name=node_name), "warning")
                return
            self.add_node_to_canvas(node_name)

    def add_node_to_canvas(self, node_name):
        """添加节点到画布"""
        if self.parent_window and hasattr(self.parent_window, 'canvas') and self.parent_window.canvas:
            self.parent_window.canvas.add_node_to_canvas(node_name)

    def open_node_folder(self, node_name):
        """打开节点文件夹"""
        if node_name not in self.nodes_data:
            themed_message(self, t("k_title_warning"), t("_k_node_not_found").format(name=node_name), "warning")
            return
        from ui.core.utils.file_utils import resolve_and_open_folder
        resolve_and_open_folder(
            self.nodes_data[node_name]['path'],
            node_name,
            parent_window=self.parent_window,
            dialog_parent=self
        )

    def view_node_log(self, node_name):
        """查看节点日志"""
        if node_name not in self.nodes_data:
            return
        node_path = self.nodes_data[node_name]['path']
        log_file = os.path.join(node_path, "logs", "listener.log")
        if not os.path.exists(log_file):
            themed_message(self, t("k_title_info"), t("k_node_no_log"), "info")
            return
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
            from ui.core.utils.log_viewer import show_log_dialog
            show_log_dialog(self, f"节点日志 - {node_name}", log_content)
        except Exception as e:
            themed_message(self, t("k_title_error"), t("_k_log_read_fail").format(err=str(e)), "error")

    def edit_node_config(self, node_name):
        """编辑节点配置"""
        if node_name not in self.nodes_data:
            return
        node_info = self.nodes_data[node_name]
        config = node_info['config']
        node_path = node_info['path']
        from ui.panels.property_panel import NodeConfigDialog
        dialog = NodeConfigDialog(node_name, config, node_path, self.parent_window)
        dialog.exec()

    # ======================== 节点删除操作 ========================

    def _force_stop_node_processes(self, node_path):
        """强制停止可能占用节点文件夹的进程"""
        import psutil
        killed_processes = []
        node_path_lower = node_path.lower().replace('/', '\\')
        for proc in psutil.process_iter(['pid', 'name', 'open_files', 'cwd']):
            try:
                try:
                    cwd = proc.cwd()
                    if cwd and node_path_lower in cwd.lower().replace('/', '\\'):
                        proc.kill()
                        killed_processes.append(f"{proc.name()} (PID={proc.pid}, cwd)")
                        continue
                except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
                    pass
                try:
                    for f in proc.open_files():
                        if f.path and node_path_lower in f.path.lower().replace('/', '\\'):
                            proc.kill()
                            killed_processes.append(f"{proc.name()} (PID={proc.pid}, file={os.path.basename(f.path)})")
                            break
                except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError):
                    pass
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
        if killed_processes:
            logger.info("强制终止了 %d 个占用节点文件夹的进程: %s", len(killed_processes), killed_processes)
        return killed_processes

    def _force_delete_directory(self, node_path):
        """强制删除目录（Windows 专用）"""
        import shutil
        parent = os.path.dirname(node_path)
        temp_name = os.path.join(parent, f"_to_delete_{int(time.time())}")
        try:
            os.rename(node_path, temp_name)
            node_path = temp_name
        except OSError:
            pass
        try:
            shutil.rmtree(node_path)
            return True, "使用 shutil.rmtree 删除成功"
        except Exception as e:
            logger.debug("shutil.rmtree 删除失败: %s", e)
        if os.name == 'nt':
            try:
                result = subprocess.run(
                    ['cmd', '/c', 'rmdir', '/s', '/q', node_path],
                    capture_output=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW
                )
                if result.returncode == 0:
                    return True, "使用 rmdir /s /q 删除成功"
                else:
                    error_msg = result.stderr.decode('utf-8', errors='ignore').strip()
                    logger.debug("rmdir 删除失败: %s", error_msg)
            except Exception as e:
                logger.debug("rmdir 命令执行失败: %s", e)
        self._force_stop_node_processes(node_path)
        time.sleep(0.5)
        try:
            shutil.rmtree(node_path)
            return True, "强制终止进程后删除成功"
        except Exception as e:
            return False, f"删除失败: {str(e)}"

    def _delete_node_async(self, node_name, callback=None):
        """异步删除节点（内部方法，不弹确认框）"""
        if node_name not in self.nodes_data:
            if callback:
                callback(False, "节点不存在")
            return
        node_path = self.nodes_data[node_name]['path']
        try:
            node_info = self.nodes_data[node_name]
            if node_info['process']:
                process = node_info['process']
                try:
                    if os.name == 'nt':
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            import signal
                            process.send_signal(signal.CTRL_BREAK_EVENT)
                            try:
                                process.wait(timeout=3)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait()
                    else:
                        import signal
                        try:
                            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                            process.wait(timeout=5)
                        except (ProcessLookupError, subprocess.TimeoutExpired):
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                            process.wait()
                except Exception as e:
                    logger.warning("停止节点时出错: %s", e)
                    try:
                        process.kill()
                        process.wait()
                    except:
                        pass
            success, msg = self._force_delete_directory(node_path)
            if not success:
                self._force_stop_node_processes(node_path)
                time.sleep(0.5)
                success, msg = self._force_delete_directory(node_path)
                if not success:
                    raise OSError(msg)
            current_group = self.group_manager.get_node_group(node_name)
            if current_group:
                self.group_manager.remove_nodes_from_group(current_group, [node_name])
            del self.nodes_data[node_name]
            try:
                if self.parent_window and hasattr(self.parent_window, 'current_project_path') and self.parent_window.current_project_path:
                    from ui.core.node_registry import NodeRegistry
                    registry = NodeRegistry(self.parent_window.current_project_path)
                    registry.load()
                    registry.unregister_node(node_name)
                    registry.save()
            except Exception:
                pass
            if self.parent_window and hasattr(self.parent_window, 'canvas') and self.parent_window.canvas:
                self.parent_window.canvas.remove_node_from_canvas(node_name)
            self.update_node_list(self.nodes_data)
            if self.parent_window and hasattr(self.parent_window, '_refresh_panels'):
                self.parent_window._refresh_panels()
            if callback:
                callback(True, None)
        except Exception as e:
            if callback:
                callback(False, str(e))

    def delete_node(self, node_name):
        """删除节点（异步执行，不阻塞 GUI）"""
        if node_name not in self.nodes_data:
            return
        if self.nodes_data[node_name].get('mounted'):
            if self.parent_window:
                self.parent_window.show_toast("外部挂载节点请使用「卸载」功能，禁止删除", "warning")
            return
        reply = themed_message(self, t("k_title_confirm_delete"), t("_k_confirm_delete_node").format(name=node_name),
            "question")
        if not reply:
            return
        QTimer.singleShot(10, lambda: self._delete_node_async(node_name, 
            lambda ok, err: self._on_delete_node_complete(node_name, ok, err)))

    def _on_delete_node_complete(self, node_name, success, error):
        """删除节点完成回调"""
        if success:
            if self.parent_window:
                self.parent_window.show_toast(t("_k_node_deleted").format(name=node_name), "success")
        else:
            themed_message(self, t("k_title_error"), t("_k_node_delete_failed").format(err=error or "Unknown error"), "error")

    # ======================== 组操作 ========================

    def _cleanup_empty_groups(self, refresh=True):
        """清理空的节点组"""
        groups = self.group_manager.get_all_groups()
        empty_groups = []
        for group_name, group_info in groups.items():
            if len(group_info['nodes']) == 0:
                if not self.group_manager.is_group_locked(group_name):
                    empty_groups.append(group_name)
        if empty_groups:
            for group_name in empty_groups:
                self.group_manager.delete_group(group_name)
            if refresh:
                self.update_node_list(self.nodes_data)
            if self.parent_window and refresh:
                self.parent_window.show_toast(t("_k_auto_deleted_groups").format(count=len(empty_groups)), "info")
            return True
        return False

    def select_all_nodes(self):
        """全选所有节点"""
        self.node_tree.selectAll()

    def deselect_all_nodes(self):
        """取消全选"""
        self.node_tree.clearSelection()

    def create_node_group(self):
        """创建新的节点组"""
        from ui.core.floating_panel import themed_input_dialog
        group_name = themed_input_dialog(self, t("k_group_create_group"), t("k_node_input_new_group_name"))
        if not group_name:
            return
        from PySide6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor("#4A90E2"), self, t("k_color_select_group"))
        if not color.isValid():
            color = QColor("#4A90E2")
        if self.group_manager.create_group(group_name, color.name()):
            selected_nodes = self.get_selected_nodes()
            if selected_nodes:
                reply = themed_message(self, t("k_title_add_to_group"), 
                    t("_k_add_to_group_prompt").format(count=len(selected_nodes), name=group_name), "question")
                if reply:
                    self.group_manager.add_nodes_to_group(group_name, selected_nodes)
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"已创建组: {group_name}", "success")

    def move_node_to_group(self, node_name, group_name):
        """移动节点到指定组"""
        if self.group_manager.is_group_locked(group_name):
            if self.parent_window:
                self.parent_window.show_toast("禁止将节点移入挂载组", "warning")
            return
        if self.group_manager.add_nodes_to_group(group_name, [node_name]):
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"已将 {node_name} 移动到组 {group_name}", "success")

    def batch_move_nodes_to_group(self, group_name):
        """批量移动选中的节点到组"""
        selected_nodes = self.get_selected_nodes()
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要移动的节点", "warning")
            return
        if self.group_manager.is_group_locked(group_name):
            if self.parent_window:
                self.parent_window.show_toast("禁止将节点移入挂载组", "warning")
            return
        if self.group_manager.add_nodes_to_group(group_name, selected_nodes):
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"已将 {len(selected_nodes)} 个节点移动到组 {group_name}", "success")

    def remove_node_from_group(self, node_name):
        """从组中移除节点"""
        current_group = self.group_manager.get_node_group(node_name)
        if current_group:
            if self.group_manager.is_group_locked(current_group):
                if self.parent_window:
                    self.parent_window.show_toast("挂载组内的节点禁止移出", "warning")
                return
            if self.group_manager.remove_nodes_from_group(current_group, [node_name]):
                self.update_node_list(self.nodes_data)
                if self.parent_window:
                    self.parent_window.show_toast(f"已将 {node_name} 从组 {current_group} 移除", "success")

    def _get_common_group(self, node_names):
        """获取多个节点的共同组"""
        if not node_names:
            return None
        groups = set()
        for node_name in node_names:
            group = self.group_manager.get_node_group(node_name)
            if group:
                groups.add(group)
            else:
                return None
        if len(groups) == 1:
            return groups.pop()
        return None

    def batch_remove_nodes_from_group(self, group_name):
        """批量从组中移除选中的节点"""
        selected_nodes = self.get_selected_nodes()
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要移除的节点", "warning")
            return
        if self.group_manager.is_group_locked(group_name):
            if self.parent_window:
                self.parent_window.show_toast("挂载组内的节点禁止移出", "warning")
            return
        if self.group_manager.remove_nodes_from_group(group_name, selected_nodes):
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"已将 {len(selected_nodes)} 个节点从组 {group_name} 移除", "success")

    def rename_group(self, group_name):
        """重命名组"""
        if self.group_manager.is_group_locked(group_name):
            if self.parent_window:
                self.parent_window.show_toast("挂载组禁止重命名", "warning")
            return
        from ui.core.floating_panel import themed_input_dialog
        new_name = themed_input_dialog(self, t("k_group_rename"), t("k_group_input_new_name"), group_name)
        if not new_name:
            return
        if new_name == group_name:
            return
        if self.group_manager.rename_group(group_name, new_name):
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"组已重命名: {group_name} -> {new_name}", "success")

    def delete_group(self, group_name):
        """删除组（保留节点）"""
        if self.group_manager.is_group_locked(group_name):
            if self.parent_window:
                self.parent_window.show_toast("挂载组禁止删除，请先卸载外部节点", "warning")
            return
        reply = themed_message(self, t("k_title_confirm_delete"), t("_k_confirm_delete_group").format(name=group_name), "question")
        if not reply:
            return
        if self.group_manager.delete_group(group_name):
            self.update_node_list(self.nodes_data)
            if self.parent_window:
                self.parent_window.show_toast(f"已删除组: {group_name}", "success")

    def toggle_group_expansion(self, group_name):
        """切换组的展开/折叠状态"""
        root = self.node_tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            data = group_item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('type') == 'group' and data.get('name') == group_name:
                group_item.setExpanded(not group_item.isExpanded())
                break

    # ======================== 批量操作 ========================

    def _start_single_node(self, node_name):
        """启动单个节点（委托给主窗口）— 内联调用点后将被移除"""
        if self.parent_window and hasattr(self.parent_window, 'start_selected_node_by_name'):
            self.parent_window.start_selected_node_by_name(node_name)

    def _stop_single_node(self, node_name):
        """停止单个节点（委托给主窗口）— 内联调用点后将被移除"""
        if self.parent_window and hasattr(self.parent_window, 'stop_selected_node_by_name'):
            self.parent_window.stop_selected_node_by_name(node_name)

    def batch_add_nodes_to_canvas(self):
        """批量添加选中的节点到画布"""
        selected_nodes = self.get_selected_nodes()
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要添加的节点", "warning")
            return
        success_count = 0
        skip_count = 0
        for node_name in selected_nodes:
            if self.parent_window and hasattr(self.parent_window, 'canvas') and self.parent_window.canvas:
                if node_name in self.parent_window.canvas.nodes:
                    skip_count += 1
                    continue
                self.parent_window.canvas.add_node_to_canvas(node_name)
                success_count += 1
        msg = f"已添加 {success_count} 个节点到画布"
        if skip_count > 0:
            msg += f"，{skip_count} 个节点已在画布上"
        if self.parent_window:
            self.parent_window.show_toast(msg, "success")

    def batch_start_nodes(self):
        """批量启动选中的节点（使用队列调度，支持拓扑排序）"""
        selected_nodes = self.get_selected_nodes()
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要启动的节点", "warning")
            return

        to_start = [n for n in selected_nodes
                    if n in self.nodes_data
                    and self.nodes_data[n].get('status') == 'stopped'
                    and not startup_queue.is_queued(n)]

        if not to_start:
            if self.parent_window:
                self.parent_window.show_toast("没有需要启动的节点", "info")
            return

        sorted_nodes = to_start
        if self.parent_window and hasattr(self.parent_window, 'canvas') and self.parent_window.canvas:
            sorted_nodes = self.parent_window.canvas.sort_nodes_by_dependency(to_start)

        if self.parent_window and hasattr(self.parent_window, 'current_project_path'):
            startup_queue.set_project_context(
                self.parent_window.current_project_path,
                self.parent_window.nodes_data,
                self.parent_window.canvas
            )

        for node_name in sorted_nodes:
            dependencies = []
            if self.parent_window and hasattr(self.parent_window, 'canvas') and self.parent_window.canvas:
                dependencies = self.parent_window.canvas.get_node_dependencies(node_name)
            startup_queue.enqueue(node_name, dependencies=dependencies)

        if self.parent_window:
            self.parent_window.show_toast(f"已将 {len(sorted_nodes)} 个节点加入启动队列", "info")
            has_dependencies = any(startup_queue.get_dependencies(n) for n in sorted_nodes)
            if has_dependencies:
                self.parent_window.show_toast("节点将按依赖顺序启动", "info")

    def batch_stop_nodes(self):
        """批量停止选中的节点（异步执行，逐个停止）"""
        selected_nodes = self.get_selected_nodes()
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要停止的节点", "warning")
            return
        to_stop = [n for n in selected_nodes if n in self.nodes_data and self.nodes_data[n].get('status') in ('running', 'idle')]
        if not to_stop:
            if self.parent_window:
                self.parent_window.show_toast("没有需要停止的节点", "info")
            return
        self.parent_window.show_toast(f"正在停止 {len(to_stop)} 个节点...", "info",
                                        node_name="batch_operation", operation_type="batch_stop")
        def stop_next(index):
            if index >= len(to_stop):
                if self.parent_window:
                    self.parent_window.show_toast(f"已停止 {len(to_stop)} 个节点", "success",
                                                    node_name="batch_operation", operation_type="batch_stop")
                return
            node_name = to_stop[index]
            self._stop_single_node(node_name)
            QTimer.singleShot(100, lambda: stop_next(index + 1))
        stop_next(0)

    def batch_open_node_folders(self):
        """批量打开选中的节点文件夹"""
        selected_nodes = self.get_selected_nodes()
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要打开的节点", "warning")
            return
        from ui.core.utils.file_utils import resolve_and_open_folder
        for node_name in selected_nodes:
            if node_name in self.nodes_data:
                node_path = self.nodes_data[node_name]['path']
                resolve_and_open_folder(node_path, node_name, self.parent_window, dialog_parent=self)
        if self.parent_window:
            self.parent_window.show_toast(f"已打开 {len(selected_nodes)} 个节点文件夹", "success")

    def batch_view_node_logs(self):
        """批量查看选中的节点日志"""
        selected_nodes = self.get_selected_nodes()
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要查看日志的节点", "warning")
            return
        all_logs = []
        for node_name in selected_nodes:
            if node_name not in self.nodes_data:
                continue
            node_path = self.nodes_data[node_name]['path']
            log_file = os.path.join(node_path, "logs", "listener.log")
            if not os.path.exists(log_file):
                continue
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    log_content = f.read()
                all_logs.append(f"{'='*60}\n节点: {node_name}\n{'='*60}\n{log_content}\n")
            except Exception as e:
                logger.warning("读取节点 %s 日志失败: %s", node_name, e)
        if not all_logs:
            themed_message(self, t("k_title_info"), t("k_node_no_log_available"), "info")
            return
        from ui.core.utils.log_viewer import show_log_dialog
        show_log_dialog(self, f"批量日志查看 - {len(selected_nodes)} 个节点", "\n".join(all_logs), width=900, height=700)

    def batch_edit_node_configs(self):
        """批量编辑选中的节点配置"""
        selected_nodes = self.get_selected_nodes()
        if not selected_nodes:
            if self.parent_window:
                self.parent_window.show_toast("请先选中要编辑配置的节点", "warning")
            return
        if len(selected_nodes) == 1:
            self.edit_node_config(selected_nodes[0])
            return
        reply = themed_message(self, t("_k_batch_edit_config"), t("_k_batch_edit_config_prompt").format(count=len(selected_nodes)), "question")
        if not reply:
            return
        for node_name in selected_nodes:
            if node_name in self.nodes_data:
                node_info = self.nodes_data[node_name]
                config = node_info['config']
                node_path = node_info['path']
                from ui.panels.property_panel import NodeConfigDialog
                dialog = NodeConfigDialog(node_name, config, node_path, self.parent_window)
                dialog.exec()

"""
BNOS 主窗口状态管理模块

负责窗口状态的保存和恢复，包括：
- 面板状态（可见性、位置）
- 窗口状态（尺寸、布局）
- 项目状态（上次打开的项目）
"""
import os
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.window_state_manager import save_state, restore_state


class MainWindowStateMixin:
    """
    主窗口状态管理 Mixin
    
    提供窗口状态保存和恢复的方法，需要与 BNOSMainWindow 配合使用。
    """
    
    def save_window_state(self):
        """保存窗口状态"""
        logger.info("进入 save_window_state()")
        save_state(self)
        logger.info("离开 save_window_state()")
    
    def restore_window_state(self):
        """恢复窗口状态"""
        logger.info("进入 restore_window_state()")
        restore_state(self)
        logger.info("离开 restore_window_state()")
    
    def _restore_panel_state(self):
        """【关键】从配置恢复面板可见性状态 - 立即创建 Dock
        
        为了让 Qt restoreState() 能找到 Dock，必须在 restoreState() 之前创建
        """
        visibility = self.app_config.get('panel_visibility', {})
        logger.info("[PANEL] 开始恢复面板状态(立即创建Dock)，配置值: %s", visibility)
        
        # 检查旧的配置项（兼容旧版本）
        old_visible = self.app_config.get('node_list_panel', {}).get('visible', False)
        logger.info("[PANEL] 旧配置项 node_list_panel.visible: %s", old_visible)
        
        # ===== 节点列表面板 =====
        # 优先使用新格式（带后缀），只有当新格式不存在时才使用旧格式（基础键）
        show_node_dock = visibility.get('node_list_dock')
        show_node_float = visibility.get('node_list_floating')
        
        # 如果新格式键不存在，使用旧格式作为备选
        if show_node_dock is None:
            show_node_dock = visibility.get('node_list', old_visible)
        if show_node_float is None:
            show_node_float = False
        
        logger.info("[PANEL] 节点列表 - dock: %s, floating: %s", show_node_dock, show_node_float)
        
        # 根据配置分别显示，不再强制优先显示Dock版
        if show_node_dock:
            logger.info("[PANEL] 立即恢复节点列表 Dock 版")
            self.toggle_node_list_panel(True)
        if show_node_float:
            logger.info("[PANEL] 立即恢复节点列表 浮动版")
            self.show_node_list_floating()
        
        # ===== 资源监测面板 =====
        show_resource_dock = visibility.get('resource_monitor_dock')
        show_resource_float = visibility.get('resource_monitor_floating')
        
        if show_resource_dock is None:
            show_resource_dock = visibility.get('resource_monitor', False)
        if show_resource_float is None:
            show_resource_float = False
        
        logger.info("[PANEL] 资源监测 - dock: %s, floating: %s", show_resource_dock, show_resource_float)
        
        if show_resource_dock:
            logger.info("[PANEL] 立即恢复资源监测 Dock 版")
            self.show_resource_monitor_dock()
        if show_resource_float:
            logger.info("[PANEL] 立即恢复资源监测 浮动版")
            self.show_resource_monitor()
        
        # ===== 节点监测面板 =====
        show_monitor_dock = visibility.get('node_monitor_dock')
        show_monitor_float = visibility.get('node_monitor_floating')
        
        if show_monitor_dock is None:
            show_monitor_dock = visibility.get('node_monitor', False)
        if show_monitor_float is None:
            show_monitor_float = False
        
        logger.info("[PANEL] 节点监测 - dock: %s, floating: %s", show_monitor_dock, show_monitor_float)
        
        if show_monitor_dock:
            logger.info("[PANEL] 立即恢复节点监测 Dock 版")
            self.show_node_monitor_dock()
        if show_monitor_float:
            logger.info("🔴 立即恢复节点监测 浮动版")
            self.show_node_monitor()
        
        # ===== 终端 Dock =====
        # 终端 Dock 由 window_state_manager 恢复，这里不处理
        show_terminal = visibility.get('terminal_dock', False)
        logger.info("[PANEL] 终端 - dock(将由window_state_manager处理): %s", show_terminal)
    
    def _restore_terminal_dock(self):
        """恢复终端 Dock 可见性（必须在主窗口 show 后调用）"""
        if not hasattr(self, '_canvas_host') or not self._canvas_host:
            return
        ch = self._canvas_host
        if not hasattr(ch, '_terminal_dock'):
            return
        
        visibility = self.app_config.get('panel_visibility', {})
        show_terminal = visibility.get('terminal_dock', True)
        
        logger.info("恢复终端 Dock (showEvent), visible=%s", show_terminal)
        
        if show_terminal:
            ch._terminal_dock.show()
            logger.info("终端恢复后: isVisible=%s", ch._terminal_dock.isVisible())
    
    def _save_panel_position(self, panel_name, panel_widget):
        """保存面板位置"""
        if hasattr(panel_widget, 'pos'):
            pos = panel_widget.pos()
            self.app_config.set(f"panel_position.{panel_name}", {
                "x": pos.x(),
                "y": pos.y()
            })
    
    def _save_panel_visibility_state(self, panel_key, visible):
        """保存单个面板的可见性状态"""
        visibility = self.app_config.get("panel_visibility", {})
        visibility[panel_key] = visible
        self.app_config.set("panel_visibility", visibility)
        self.app_config.save()
    
    def _save_panel_visibility(self):
        """保存所有面板的可见性状态到配置"""
        # 获取当前配置中的状态（保留已关闭面板的状态）
        current_visibility = self.app_config.get('panel_visibility', {})
        
        # 检查面板是否真正可见（而不仅仅是对象是否存在）
        def is_panel_visible(panel):
            if panel is None:
                return None  # 返回 None 表示面板对象不存在，不更新状态
            visible = panel.isVisible()
            logger.debug("面板可见性检查: %s = %s", type(panel).__name__, visible)
            return visible
        
        # 只更新存在的面板状态，不存在的面板保留配置中的值
        visibility = current_visibility.copy()
        
        # 更新存在的面板状态
        dock_panels = [
            ('node_list_dock', self.node_list_panel),
            ('resource_monitor_dock', self.resource_monitor),
            ('node_monitor_dock', getattr(self, 'node_monitor_dock', None)),
        ]
        floating_panels = [
            ('node_list_floating', getattr(self, 'node_list_floating', None)),
            ('resource_monitor_floating', getattr(self, 'resource_monitor_floating', None)),
            ('node_monitor_floating', getattr(self, 'node_monitor', None)),
        ]
        
        for key, panel in dock_panels + floating_panels:
            visible = is_panel_visible(panel)
            if visible is not None:
                visibility[key] = visible
        
        # 更新旧格式（兼容旧配置）
        visibility['node_list'] = is_panel_visible(self.node_list_panel) or is_panel_visible(getattr(self, 'node_list_floating', None)) or False
        visibility['resource_monitor'] = is_panel_visible(self.resource_monitor) or is_panel_visible(getattr(self, 'resource_monitor_floating', None)) or False
        visibility['node_monitor'] = is_panel_visible(getattr(self, 'node_monitor_dock', None)) or is_panel_visible(getattr(self, 'node_monitor', None)) or False
        
        # 保存终端 Dock 可见性（在 CanvasHost 内部）
        if hasattr(self, '_canvas_host') and self._canvas_host:
            ch = self._canvas_host
            if hasattr(ch, '_terminal_dock'):
                term_visible = ch._terminal_dock.isVisible()
                visibility['terminal_dock'] = term_visible
                logger.info("[SAVE] _save_panel_visibility: terminal_dock = %s", term_visible)
        
        logger.info("保存面板可见性状态: %s", visibility)
        self.app_config.set('panel_visibility', visibility)
    
    def _restore_terminal_dock(self):
        """恢复终端 Dock 的可见性
        
        注意：仅在终端已初始化（画布已创建）时才恢复可见性。
        如果终端尚未初始化，则跳过 —— 它将在第一个画布创建时自动初始化。
        """
        visibility = self.app_config.get("panel_visibility", {})
        show_terminal = visibility.get("terminal_dock", True)
        
        if hasattr(self, '_canvas_host') and self._canvas_host:
            ch = self._canvas_host
            if hasattr(ch, '_terminal_dock') and ch._terminal_dock:
                if show_terminal:
                    ch._terminal_dock.show()
                else:
                    ch._terminal_dock.hide()
    
    def auto_open_last_project(self):
        """自动打开上次打开的项目：
        - 如果有上次打开的项目，自动打开
        - 如果没有，保持空白，等待用户手动打开项目
        """
        # 检查是否有上次打开的项目
        last_project = self.app_config.get("last_project")
        if last_project and isinstance(last_project, str) and os.path.exists(last_project):
            # 有上次打开的项目，自动打开
            logger.info("自动打开上次项目: %s", last_project)
            self._auto_open_project(last_project)
        else:
            logger.info("没有上次项目或项目不存在，等待用户手动打开项目")
    
    def _auto_open_project(self, project_dir):
        """内部方法：自动打开指定项目
        
        这个方法类似于 project_open，但不需要用户交互
        """
        # 检查项目是否已经打开
        if hasattr(self, '_canvas_host') and self._canvas_host:
            if self._canvas_host.is_project_open(project_dir):
                logger.info("项目已经打开，无需重复打开: %s", project_dir)
                return
        
        # 验证是否为有效项目
        nodes_dir = os.path.join(project_dir, "nodes")
        has_nodes = os.path.isdir(nodes_dir)
        has_layout = os.path.isfile(os.path.join(project_dir, "canvas_layout.json"))
        
        if not has_nodes and not has_layout:
            logger.warning("不是有效项目目录: %s", project_dir)
            return
        
        # 确保 nodes/ 存在
        if not has_nodes:
            os.makedirs(nodes_dir, exist_ok=True)
        
        # 加载项目数据
        project_name = os.path.basename(project_dir)
        self.current_project_path = project_dir
        self.nodes_data.clear()
        self.connections.clear()
        
        # 同步加载项目
        from ui.core.project_manager import project_refresh
        project_refresh(self, async_mode=False)
        
        # 创建画布（_create_canvas_dock 内部已调用一次 load_layout，无需再调）
        if hasattr(self, '_canvas_host'):
            self._canvas_host.add_canvas_dock(project_name, project_dir)
        
        # ===== 关键：恢复 CanvasHost 的状态（包括分割条位置） =====
        from ui.core.window_state_manager import restore_canvas_host_state
        from PySide6.QtCore import QTimer
        # 给一点时间让画布 Dock 完全创建
        QTimer.singleShot(200, lambda: restore_canvas_host_state(self))
        
        # 保存项目到配置
        self.app_config.set("last_project", self.current_project_path)
        self.app_config.save()
        
        self.show_toast(f"已自动打开项目: {project_name}", "success")

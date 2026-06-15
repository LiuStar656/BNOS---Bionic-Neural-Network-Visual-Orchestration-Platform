"""
项目管理 — 新建/打开/刷新项目，扫描并加载节点数据
"""
import os
import json
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.node_registry import NodeRegistry
from ui.core.node_process import detect_running_nodes
from ui.core.utils.dialog_utils import pick_folder, themed_input, themed_message


def _canvas(mw):
    """安全访问 canvas，进程模式返回 None"""
    return getattr(mw, 'canvas', None)

def _canvas_call(mw, method, *args, **kwargs):
    c = _canvas(mw)
    if c and hasattr(c, method):
        return getattr(c, method)(*args, **kwargs)


def project_new(main_window):
    """新建项目：选父目录 → 输入名称 → 创建文件夹+nodes/ → 创建新标签页"""
    # 1. 选上级目录
    parent_dir = pick_folder(main_window, t("k_project_select_parent_dir"))
    if not parent_dir:
        return

    # 2. 输入项目名
    proj_name = themed_input(main_window, t("k_project_new"), t("k_project_input_name"))
    if not proj_name or not proj_name.strip():
        return

    # 3. 创建项目文件夹
    project_dir = os.path.join(parent_dir, proj_name.strip())
    if os.path.exists(project_dir):
        themed_message(main_window, t("k_title_warning"), f"文件夹已存在: {project_dir}", "warning")
        return
    
    # 检查项目是否已经打开（通过CanvasHost）
    if hasattr(main_window, '_canvas_host') and main_window._canvas_host:
        if main_window._canvas_host.is_project_open(project_dir):
            themed_message(main_window, t("k_title_info"), f"项目 '{proj_name.strip()}' 已经打开，无需重复创建。", "info")
            return
    
    os.makedirs(project_dir)
    nodes_dir = os.path.join(project_dir, "nodes")
    os.makedirs(nodes_dir, exist_ok=True)

    # 更新项目状态
    main_window.current_project_path = project_dir
    main_window.nodes_data.clear()
    main_window.connections.clear()
    _canvas_call(main_window, 'clear_canvas')
    project_refresh(main_window)
    
    # 4. 创建新画布Dock，使用项目名作为标签名（通过CanvasHost）
    if hasattr(main_window, '_canvas_host'):
        main_window._canvas_host.add_canvas_dock(proj_name.strip(), project_dir)
    
    main_window.show_toast(f"已创建项目: {proj_name.strip()}", "success")
    
    # 保存项目到配置文件
    main_window.app_config.set("last_project", main_window.current_project_path)
    main_window.app_config.save()


def project_open(main_window):
    """打开项目：选文件夹 → 异步加载项目结构 + 创建画布"""
    project_dir = pick_folder(main_window, t("k_project_open_dir"))
    if not project_dir:
        return

    # 检查项目是否已经打开
    if hasattr(main_window, '_canvas_host') and main_window._canvas_host:
        if main_window._canvas_host.is_project_open(project_dir):
            project_name = os.path.basename(project_dir)
            themed_message(main_window, t("k_title_info"), f"项目 '{project_name}' 已经打开，无需重复打开。", "info")
            return

    # 验证是否为有效项目（有 nodes/ 目录或 canvas_layout.json）
    nodes_dir = os.path.join(project_dir, "nodes")
    has_nodes = os.path.isdir(nodes_dir)
    has_layout = os.path.isfile(os.path.join(project_dir, "canvas_layout.json"))

    if not has_nodes and not has_layout:
        themed_message(main_window, t("k_title_warning"), f"未识别为有效项目目录：\n{project_dir}\n\n"
                            f"项目中需包含 nodes/ 文件夹 或 canvas_layout.json", "warning")
        return

    # 确保 nodes/ 存在（旧项目可能只有 layout）
    if not has_nodes:
        os.makedirs(nodes_dir, exist_ok=True)

    project_name = os.path.basename(project_dir)

    # 立即显示提示，后续异步加载
    main_window.show_toast(f"正在打开项目: {project_name}...", "info")

    def _open_project_async():
        """异步加载项目 — 延迟到事件循环避免阻塞 Toast 响应"""
        main_window.current_project_path = project_dir
        main_window.nodes_data.clear()
        main_window.connections.clear()

        # 同步加载节点数据（_open_project_async 本身已是延迟回调，不会阻塞 UI 响应）
        # 必须同步完成 — add_canvas_dock 会立即调用 load_layout，依赖 nodes_data
        project_refresh(main_window, async_mode=False)

        # 创建新画布Dock（必须在主线程，依赖 nodes_data 已填充）
        if hasattr(main_window, '_canvas_host'):
            main_window._canvas_host.add_canvas_dock(project_name, project_dir)

        # 恢复 CanvasHost 状态（包括分割条位置）
        from ui.core.window_state_manager import restore_canvas_host_state
        QTimer.singleShot(300, lambda: restore_canvas_host_state(main_window))

        # 保存项目到配置文件
        main_window.app_config.set("last_project", main_window.current_project_path)
        main_window.app_config.save()

    QTimer.singleShot(10, _open_project_async)


def project_refresh(main_window, async_mode=True):
    """刷新节点列表
    
    参数:
        async_mode: 是否异步执行，默认为True。打开项目时设为False以同步加载。
    """
    if not main_window.current_project_path:
        main_window.show_toast(t("k_project_no_project"), "warning")
        return

    project_path = os.path.abspath(main_window.current_project_path)
    nodes_dir = os.path.join(project_path, "nodes")

    if not os.path.exists(nodes_dir):
        main_window.show_toast(t("k_project_nodes_not_exist"), "warning")
        return

    if async_mode:
        # 立即显示正在刷新
        main_window.show_toast("正在刷新节点列表...", "info")
        # 异步执行刷新
        QTimer.singleShot(10, lambda: _project_refresh_async(main_window, project_path, nodes_dir))
    else:
        # 同步执行刷新（用于打开项目时）
        _project_refresh_async(main_window, project_path, nodes_dir)

def _project_refresh_async(main_window, project_path, nodes_dir):
    """异步刷新节点列表（内部方法）"""
    from ui.core.node_registry import NodeRegistry
    from ui.core.node_process import detect_running_nodes
    
    logger.info(t("k_log_load_node"))
    logger.debug("项目路径: %s", project_path)
    logger.debug("Nodes 目录: %s", nodes_dir)

    main_window.nodes_data.clear()
    
    # 扫描节点目录
    try:
        for item in os.listdir(nodes_dir):
            node_path = os.path.join(nodes_dir, item)
            node_path = os.path.abspath(node_path)
            node_path = os.path.normpath(node_path)

            if not os.path.isdir(node_path):
                continue

            config_path = os.path.join(node_path, "config.json")
            if not os.path.exists(config_path):
                continue

            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                node_name = config.get('node_name', item)

                expected_path = os.path.join(nodes_dir, item)
                expected_path = os.path.abspath(expected_path)
                expected_path = os.path.normpath(expected_path)

                if node_path != expected_path:
                    logger.warning("节点 '%s' 路径不一致: 期望=%s, 实际=%s", item, expected_path, node_path)
                    node_path = expected_path

                main_window.nodes_data[node_name] = {
                    'config': config,
                    'path': node_path,
                    'process': None,
                    'status': 'stopped'
                }

                logger.info("加载节点: %s (文件夹=%s)", node_name, item)
                logger.debug("   路径: %s, 存在: %s", node_path, os.path.exists(node_path))

            except Exception as e:
                logger.error("加载节点 %s 失败: %s", item, e)
                import traceback
                traceback.print_exc()

        logger.info("共加载 %d 个节点", len(main_window.nodes_data))

        # 同步节点注册表
        try:
            registry = NodeRegistry(main_window.current_project_path)
            registry.load()
            scan_result = {name: info['path'] for name, info in main_window.nodes_data.items()}
            registry.sync_from_scan(scan_result)
            registry.save()
            logger.info("节点注册表已同步: active=%d, missing=%d, total=%d",
                        registry.active_count, registry.missing_count, registry.node_count)

            mounted_nodes = registry.get_mounted_nodes()
            for m_name, m_info in mounted_nodes.items():
                if m_name not in main_window.nodes_data and m_info.get("status") == "active":
                    m_path = m_info.get("path", "")
                    m_config_path = os.path.join(m_path, "config.json")
                    m_mount_root = m_info.get("mount_root", "")
                    try:
                        if os.path.exists(m_config_path):
                            with open(m_config_path, 'r', encoding='utf-8') as f:
                                m_config = json.load(f)
                        else:
                            m_config = {'node_name': m_name}
                        main_window.nodes_data[m_name] = {
                            'config': m_config,
                            'path': m_path,
                            'process': None,
                            'status': 'stopped',
                            'mounted': True,
                            'mount_root': m_mount_root
                        }
                        logger.info("恢复挂载节点: %s (mount_root=%s)", m_name, m_mount_root)

                        # 恢复锁定组（只有当节点列表面板已创建时）
                        if main_window.node_list_panel:
                            gm = main_window.node_list_panel.group_manager
                            if not gm.groups.get(m_mount_root):
                                gm.create_group(m_mount_root, "#E67E22")
                            gm.add_nodes_to_group(m_mount_root, [m_name])
                            gm.lock_group(m_mount_root)
                    except Exception as ex:
                        logger.warning("恢复挂载节点 %s 失败: %s", m_name, ex)
            logger.info("共恢复 %d 个挂载节点", len(mounted_nodes))
        except Exception as e:
            logger.warning("节点注册表同步失败: %s", e)

        # 检测运行中的节点
        running = detect_running_nodes(main_window.nodes_data)
        
        # 在主线程中更新 UI
        def update_ui():
            # 更新节点列表面板
            if main_window.node_list_panel:
                main_window.node_list_panel.set_project_path(main_window.current_project_path)
                main_window.node_list_panel.update_node_list(main_window.nodes_data)
            
            _canvas_call(main_window, 'sync_all_nodes_display')

            if running:
                for name, pid in running:
                    if main_window.node_list_panel:
                        main_window.node_list_panel.update_node_status(name, 'running')
                    _canvas_call(main_window, 'update_node_status', name, 'running')
                main_window.show_toast(f"检测到 {len(running)} 个节点在后台运行", "info")
            else:
                main_window.show_toast(f"已刷新 {len(main_window.nodes_data)} 个节点", "success")
        
        QTimer.singleShot(10, update_ui)
    except Exception as e:
        QTimer.singleShot(10, lambda: main_window.show_toast(f"刷新失败: {e}", "error"))
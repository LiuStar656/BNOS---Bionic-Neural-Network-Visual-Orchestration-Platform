"""
项目管理 — 新建/打开/刷新项目，扫描并加载节点数据

性能优化：磁盘扫描与 JSON 解析等耗时操作通过 ProjectLoadWorker
在后台线程完成，主线程仅负责创建画布与 UI 更新。
"""
import os
import json
from PySide6.QtWidgets import QMessageBox
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.project_load_worker import ProjectLoadWorker
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

    # 立即显示提示（Toast 不阻塞事件循环），然后在后台线程扫描磁盘
    main_window.show_toast(f"正在打开项目: {project_name}...", "info")

    # —— 在主线程先重置状态（纯内存操作，毫秒级）——
    main_window.current_project_path = project_dir
    main_window.nodes_data.clear()
    main_window.connections.clear()

    # —— Worker：在后台线程做磁盘扫描 + JSON 解析 ——
    worker = ProjectLoadWorker(project_dir, parent=main_window)

    def _on_progress(pct, msg):
        """加载进度更新（回到主线程）"""
        # 每 20% 才刷新一次 Toast，避免 UI 抖动
        if pct % 20 == 0 or pct == 100:
            main_window.show_toast(f"打开项目: {msg} ({pct}%)", "info")

    def _on_finished(nodes_data, mounted_nodes, running_nodes):
        """加载完成 → 回到主线程填充数据并创建画布"""
        # 1) 填充 nodes_data（纯字典赋值）
        main_window.nodes_data.clear()
        for name, info in nodes_data.items():
            main_window.nodes_data[name] = info

        # 2) 处理挂载节点的锁定组 UI（Dock版 + 浮动版）
        for m in mounted_nodes:
            m_mount_root = m['mount_root']
            _panels_to_update = []
            if hasattr(main_window, 'node_list_panel') and main_window.node_list_panel:
                _panels_to_update.append(main_window.node_list_panel)
            if hasattr(main_window, 'node_list_floating') and main_window.node_list_floating:
                _panels_to_update.append(main_window.node_list_floating)
            for panel in _panels_to_update:
                gm = panel.group_manager
                if not gm.groups.get(m_mount_root):
                    gm.create_group(m_mount_root, "#E67E22")
                gm.add_nodes_to_group(m_mount_root, [m['name']])
                gm.lock_group(m_mount_root)

        # 3) 创建画布Dock（必须在主线程，依赖 nodes_data 已填充）
        if hasattr(main_window, '_canvas_host'):
            main_window._canvas_host.add_canvas_dock(project_name, project_dir)

        # 4) 更新面板 + 画布 UI（不调用 restore_canvas_host_state 避免用旧状态隐藏新画布 dock）
        _apply_after_refresh(main_window, running_nodes)

        # 5) 保存项目到配置文件
        main_window.app_config.set("last_project", main_window.current_project_path)
        main_window.app_config.save()

        main_window.show_toast(f"已打开项目: {project_name} ({len(nodes_data)} 个节点)", "success")

    def _on_failed(err_msg):
        main_window.show_toast(f"打开项目失败: {err_msg}", "error")

    worker.progress.connect(_on_progress)
    worker.finished.connect(_on_finished)
    worker.failed.connect(_on_failed)
    worker.start()


def project_refresh(main_window, async_mode=True):
    """刷新节点列表 — 走 ProjectLoadWorker 异步扫描磁盘

    参数:
        async_mode: 是否异步执行（当前始终异步，保留参数为了向后兼容）
    """
    if not main_window.current_project_path:
        main_window.show_toast(t("k_project_no_project"), "warning")
        return

    project_path = os.path.abspath(main_window.current_project_path)
    nodes_dir = os.path.join(project_path, "nodes")

    if not os.path.exists(nodes_dir):
        main_window.show_toast(t("k_project_nodes_not_exist"), "warning")
        return

    main_window.show_toast("正在刷新节点列表...", "info")

    # —— Worker：异步扫描磁盘 ——
    worker = ProjectLoadWorker(project_path, parent=main_window)

    def _on_progress(pct, msg):
        if pct in (30, 60, 100):
            main_window.show_toast(f"刷新中: {msg} ({pct}%)", "info")

    def _on_finished(nodes_data, mounted_nodes, running_nodes):
        # 主线程填充数据
        main_window.nodes_data.clear()
        for name, info in nodes_data.items():
            main_window.nodes_data[name] = info

        # 挂载节点锁定组 UI（Dock版 + 浮动版）
        for m in mounted_nodes:
            m_mount_root = m['mount_root']
            _panels_to_update = []
            if hasattr(main_window, 'node_list_panel') and main_window.node_list_panel:
                _panels_to_update.append(main_window.node_list_panel)
            if hasattr(main_window, 'node_list_floating') and main_window.node_list_floating:
                _panels_to_update.append(main_window.node_list_floating)
            for panel in _panels_to_update:
                gm = panel.group_manager
                if not gm.groups.get(m_mount_root):
                    gm.create_group(m_mount_root, "#E67E22")
                gm.add_nodes_to_group(m_mount_root, [m['name']])
                gm.lock_group(m_mount_root)

        # 统一 UI 更新
        _apply_after_refresh(main_window, running_nodes)

    def _on_failed(err_msg):
        main_window.show_toast(f"刷新失败: {err_msg}", "error")

    worker.progress.connect(_on_progress)
    worker.finished.connect(_on_finished)
    worker.failed.connect(_on_failed)
    worker.start()


def _apply_after_refresh(main_window, running_nodes):
    """刷新完成后在主线程统一更新面板与画布

    参数:
        running_nodes: [(name, pid), ...] （由 Worker 传回的后台运行节点列表）  
    """
    # 1) 更新节点列表面板（Dock 版 + 浮动版）
    if hasattr(main_window, 'node_list_panel') and main_window.node_list_panel:
        main_window.node_list_panel.set_project_path(main_window.current_project_path)
        main_window.node_list_panel.update_node_list(main_window.nodes_data)

    if hasattr(main_window, 'node_list_floating') and main_window.node_list_floating:
        if hasattr(main_window.node_list_floating, 'set_project_path') and main_window.current_project_path:
            main_window.node_list_floating.set_project_path(main_window.current_project_path)
        main_window.node_list_floating.update_node_list(main_window.nodes_data)

    # 2) 画布：同步所有节点的显示状态
    _canvas_call(main_window, 'sync_all_nodes_display')

    # 3) 运行状态刷新
    if running_nodes:
        for name, pid in running_nodes:
            if hasattr(main_window, 'node_list_panel') and main_window.node_list_panel:
                main_window.node_list_panel.update_node_status(name, 'running')
            if hasattr(main_window, 'node_list_floating') and main_window.node_list_floating:
                main_window.node_list_floating.update_node_status(name, 'running')
            _canvas_call(main_window, 'update_node_status', name, 'running')
        main_window.show_toast(f"检测到 {len(running_nodes)} 个节点在后台运行", "info")
    else:
        main_window.show_toast(f"已刷新 {len(main_window.nodes_data)} 个节点", "success")
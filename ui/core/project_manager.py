"""
项目管理 — 新建/打开/刷新项目，扫描并加载节点数据
"""
import os
import json
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.node_registry import NodeRegistry
from ui.core.node_process import detect_running_nodes


def project_new(main_window):
    """新建项目"""
    if main_window.current_project_path:
        main_window.canvas.save_layout(main_window.current_project_path)

    project_dir = QFileDialog.getExistingDirectory(
        main_window, t("k_project_select_dir"), "",
        QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
    )

    if not project_dir:
        return

    nodes_dir = os.path.join(project_dir, "nodes")
    if not os.path.exists(nodes_dir):
        reply = QMessageBox.question(
            main_window, t("k_project_create_nodes_dir"),
            f"在 {project_dir} 下创建 nodes/ 目录？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            os.makedirs(nodes_dir, exist_ok=True)
        else:
            return

    main_window.current_project_path = project_dir
    main_window.nodes_data.clear()
    main_window.connections.clear()
    main_window.canvas.clear_canvas()

    project_refresh(main_window)

    main_window.show_toast(f"已创建项目: {os.path.basename(project_dir)}", "success")


def project_open(main_window):
    """打开项目"""
    if main_window.current_project_path:
        main_window.canvas.save_layout(main_window.current_project_path)

    project_dir = QFileDialog.getExistingDirectory(
        main_window, t("k_project_open_dir"), "",
        QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
    )

    if not project_dir:
        return

    nodes_dir = os.path.join(project_dir, "nodes")
    if not os.path.exists(nodes_dir):
        reply = QMessageBox.question(
            main_window, t("k_project_no_nodes_dir"),
            f"{project_dir} 下未找到 nodes/ 目录，是否创建？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            os.makedirs(nodes_dir, exist_ok=True)
        else:
            return

    main_window.current_project_path = project_dir
    main_window.nodes_data.clear()
    main_window.connections.clear()
    main_window.canvas.clear_canvas()

    project_refresh(main_window)
    main_window.canvas.load_layout(project_dir)

    main_window.show_toast(f"已打开项目: {os.path.basename(project_dir)}", "success")


def project_refresh(main_window):
    """刷新节点列表：扫描 nodes/ 目录、同步注册表、恢复挂载节点"""
    if not main_window.current_project_path:
        main_window.show_toast(t("k_project_no_project"), "warning")
        return

    project_path = os.path.abspath(main_window.current_project_path)
    nodes_dir = os.path.join(project_path, "nodes")

    if not os.path.exists(nodes_dir):
        main_window.show_toast(t("k_project_nodes_not_exist"), "warning")
        return

    logger.info(t("k_log_load_node"))
    logger.debug("项目路径: %s", project_path)
    logger.debug("Nodes 目录: %s", nodes_dir)

    main_window.nodes_data.clear()
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
                except Exception as ex:
                    logger.warning("恢复挂载节点 %s 失败: %s", m_name, ex)
        logger.info("共恢复 %d 个挂载节点", len(mounted_nodes))
    except Exception as e:
        logger.warning("节点注册表同步失败: %s", e)

    main_window.node_list_panel.set_project_path(main_window.current_project_path)
    main_window.node_list_panel.update_node_list(main_window.nodes_data)
    main_window.canvas.sync_all_nodes_display()

    running = detect_running_nodes(main_window.nodes_data)
    if running:
        for name, pid in running:
            main_window.node_list_panel.update_node_status(name, 'running')
            main_window.canvas.update_node_status(name, 'running')
        main_window.show_toast(f"检测到 {len(running)} 个节点在后台运行", "info")

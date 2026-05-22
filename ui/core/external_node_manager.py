"""
外部节点管理 — 挂载/卸载外部节点到当前项目
"""
import os
import json
from PyQt6.QtWidgets import QFileDialog
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.node_registry import NodeRegistry


def mount_node(main_window):
    """挂载外部节点到当前项目"""
    if not main_window.current_project_path:
        main_window.show_toast(t("k_project_no_project"), "warning")
        return

    folder_path = QFileDialog.getExistingDirectory(
        main_window, t("k_node_select_external"), "",
        QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
    )

    if not folder_path:
        return

    folder_path = os.path.abspath(folder_path)
    config_path = os.path.join(folder_path, "config.json")

    if not os.path.exists(config_path):
        main_window.show_toast(f"所选文件夹中未找到 config.json:\n{folder_path}", "warning")
        return

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        main_window.show_toast(f"读取 config.json 失败: {e}", "error")
        return

    node_name = config.get('node_name', os.path.basename(folder_path))

    if node_name in main_window.nodes_data:
        main_window.show_toast(f"节点 '{node_name}' 已存在，无法重复挂载", "warning")
        return

    mount_root = os.path.dirname(folder_path)
    mount_root = os.path.abspath(mount_root)

    main_window.nodes_data[node_name] = {
        'config': config,
        'path': folder_path,
        'process': None,
        'status': 'stopped',
        'mounted': True,
        'mount_root': mount_root
    }

    try:
        registry = NodeRegistry(main_window.current_project_path)
        registry.load()
        registry.register_node(node_name, folder_path, mount_root=mount_root)
        registry.save()
        logger.info("挂载节点已注册: name=%s, path=%s, mount_root=%s",
                    node_name, folder_path, mount_root)
    except Exception as e:
        logger.warning("挂载节点注册表同步失败: %s", e)

    mount_group_name = mount_root
    if not main_window.node_list_panel.group_manager.groups.get(mount_group_name):
        main_window.node_list_panel.group_manager.create_group(mount_group_name, "#E67E22")
    main_window.node_list_panel.group_manager.add_nodes_to_group(mount_group_name, [node_name])
    main_window.node_list_panel.group_manager.lock_group(mount_group_name)

    main_window.node_list_panel.set_project_path(main_window.current_project_path)
    main_window.node_list_panel.update_node_list(main_window.nodes_data)
    main_window.canvas.sync_all_nodes_display()

    main_window.show_toast(f"已挂载外部节点: {node_name}", "success")
    logger.info("外部节点挂载完成: %s -> %s (group=%s)", node_name, folder_path, mount_group_name)


def unmount_node(main_window, node_name):
    """卸载外部挂载节点"""
    if node_name not in main_window.nodes_data:
        return

    node_info = main_window.nodes_data[node_name]
    if not node_info.get('mounted'):
        main_window.show_toast(f"节点 '{node_name}' 不是外部挂载节点", "warning")
        return

    mount_root = node_info.get('mount_root')
    mount_group_name = mount_root

    try:
        registry = NodeRegistry(main_window.current_project_path)
        registry.load()
        registry.unregister_node(node_name)
        registry.save()
    except Exception:
        pass

    if mount_group_name:
        main_window.node_list_panel.group_manager.remove_nodes_from_group(mount_group_name, [node_name])
        remaining = main_window.node_list_panel.group_manager.get_group_nodes(mount_group_name)
        if not remaining:
            main_window.node_list_panel.group_manager.unlock_group(mount_group_name)
            main_window.node_list_panel.group_manager.delete_group(mount_group_name)

    del main_window.nodes_data[node_name]
    main_window.node_list_panel.update_node_list(main_window.nodes_data)
    main_window.canvas.remove_node_from_canvas(node_name)

    main_window.show_toast(f"已卸载外部节点: {node_name}", "success")

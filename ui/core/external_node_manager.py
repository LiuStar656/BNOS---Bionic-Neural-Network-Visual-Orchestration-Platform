"""
外部节点管理 — 挂载/卸载外部节点到当前项目
"""
import os
import json
from PyQt6.QtCore import QTimer
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.node_registry import NodeRegistry
from ui.core.utils.dialog_utils import pick_folder
from ui.core.project_manager import _canvas_call


def mount_node(main_window):
    """挂载外部节点到当前项目（异步执行，不阻塞 GUI）"""
    if not main_window.current_project_path:
        main_window.show_toast(t("k_project_no_project"), "warning")
        return

    folder_path = pick_folder(main_window, t("k_node_select_external"))

    if not folder_path:
        return

    # 立即显示正在处理
    main_window.show_toast("正在处理挂载请求...", "info")

    # 异步执行挂载
    QTimer.singleShot(10, lambda: _mount_node_async(main_window, folder_path))

def _mount_node_async(main_window, folder_path):
    """异步执行挂载（内部方法）"""
    try:
        folder_path = os.path.abspath(folder_path)
        config_path = os.path.join(folder_path, "config.json")

        if not os.path.exists(config_path):
            QTimer.singleShot(10, lambda: main_window.show_toast(f"所选文件夹中未找到 config.json:\n{folder_path}", "warning"))
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        node_name = config.get('node_name', os.path.basename(folder_path))

        if node_name in main_window.nodes_data:
            QTimer.singleShot(10, lambda: main_window.show_toast(f"节点 '{node_name}' 已存在，无法重复挂载", "warning"))
            return

        mount_root = os.path.dirname(folder_path)
        mount_root = os.path.abspath(mount_root)

        # 更新节点数据
        main_window.nodes_data[node_name] = {
            'config': config,
            'path': folder_path,
            'process': None,
            'status': 'stopped',
            'mounted': True,
            'mount_root': mount_root
        }

        # 注册到节点注册表
        try:
            registry = NodeRegistry(main_window.current_project_path)
            registry.load()
            registry.register_node(node_name, folder_path, mount_root=mount_root)
            registry.save()
            logger.info("挂载节点已注册: name=%s, path=%s, mount_root=%s",
                        node_name, folder_path, mount_root)
        except Exception as e:
            logger.warning("挂载节点注册表同步失败: %s", e)

        # 创建组
        main_window.node_list_panel.set_project_path(main_window.current_project_path)
        mount_group_name = mount_root
        if not main_window.node_list_panel.group_manager.groups.get(mount_group_name):
            main_window.node_list_panel.group_manager.create_group(mount_group_name, "#E67E22")
        main_window.node_list_panel.group_manager.add_nodes_to_group(mount_group_name, [node_name])
        main_window.node_list_panel.group_manager.lock_group(mount_group_name)
        main_window.node_list_panel.group_manager.save_groups()

        # 在主线程中更新 UI
        def update_ui():
            main_window.node_list_panel.update_node_list(main_window.nodes_data)
            _canvas_call(main_window, 'sync_all_nodes_display')
            main_window.show_toast(f"已挂载外部节点: {node_name}", "success")
            logger.info("外部节点挂载完成: %s -> %s (group=%s)", node_name, folder_path, mount_group_name)
        
        QTimer.singleShot(10, update_ui)
    except Exception as e:
        QTimer.singleShot(10, lambda: main_window.show_toast(f"挂载失败: {e}", "error"))


def unmount_node(main_window, node_name):
    """卸载外部挂载节点（异步执行，不阻塞 GUI）"""
    if node_name not in main_window.nodes_data:
        return

    node_info = main_window.nodes_data[node_name]
    if not node_info.get('mounted'):
        main_window.show_toast(f"节点 '{node_name}' 不是外部挂载节点", "warning")
        return

    # 立即显示正在处理
    main_window.show_toast("正在卸载节点...", "info")

    # 异步执行卸载
    QTimer.singleShot(10, lambda: _unmount_node_async(main_window, node_name))

def _unmount_node_async(main_window, node_name):
    """异步执行卸载（内部方法）"""
    try:
        node_info = main_window.nodes_data[node_name]
        mount_root = node_info.get('mount_root')
        mount_group_name = mount_root

        # 从注册表注销
        try:
            registry = NodeRegistry(main_window.current_project_path)
            registry.load()
            registry.unregister_node(node_name)
            registry.save()
        except Exception:
            pass

        # 从组中移除
        if mount_group_name:
            main_window.node_list_panel.group_manager.remove_nodes_from_group(mount_group_name, [node_name])
            remaining = main_window.node_list_panel.group_manager.get_group_nodes(mount_group_name)
            if not remaining:
                main_window.node_list_panel.group_manager.unlock_group(mount_group_name)
                main_window.node_list_panel.group_manager.delete_group(mount_group_name)

        # 从节点数据中移除
        del main_window.nodes_data[node_name]
        main_window.node_list_panel.group_manager.save_groups()

        # 在主线程中更新 UI
        def update_ui():
            main_window.node_list_panel.update_node_list(main_window.nodes_data)
            _canvas_call(main_window, 'remove_node_from_canvas', node_name)
            main_window.show_toast(f"已卸载外部节点: {node_name}", "success")
        
        QTimer.singleShot(10, update_ui)
    except Exception as e:
        QTimer.singleShot(10, lambda: main_window.show_toast(f"卸载失败: {e}", "error"))

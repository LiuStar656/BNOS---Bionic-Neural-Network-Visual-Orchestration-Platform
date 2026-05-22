"""
通用文件工具 — 消除 node_list_panel 和 property_panel 中的重复代码
"""
import os
import subprocess
import platform
from PyQt6.QtWidgets import QMessageBox
from ui.core.utils.dialog_utils import themed_message
from ui.core.logger import logger
from ui.core.i18n import t


def resolve_and_open_folder(node_path, node_name, parent_window=None, dialog_parent=None):
    """
    路径修正 + 备用查找 + 系统文件管理器打开

    Args:
        node_path: 节点文件夹路径（可能是相对路径）
        node_name: 节点名称（用于备用查找和错误提示）
        parent_window: 主窗口引用（用于备用路径查找）
        dialog_parent: 对话框父窗口（None 则用 node_path 所在窗口）

    Returns:
        bool: 是否成功打开
    """
    # 1. 路径修正
    corrected_path = os.path.normpath(os.path.abspath(node_path))

    if corrected_path != node_path:
        logger.debug("[file_utils] 路径已修正: %s → %s", node_path, corrected_path)

    # 2. 主路径不存在 → 从主窗口备用查找
    if not os.path.exists(corrected_path):
        logger.warning("[file_utils] 路径不存在: %s", corrected_path)

        if parent_window and hasattr(parent_window, 'nodes_data'):
            node_info = parent_window.nodes_data.get(node_name)
            if node_info and 'path' in node_info:
                alt_path = os.path.normpath(os.path.abspath(node_info['path']))
                logger.debug("[file_utils] 尝试备用路径: %s", alt_path)
                if os.path.exists(alt_path):
                    corrected_path = alt_path
                    logger.debug("[file_utils] 使用备用路径")

    # 3. 仍然不存在 → 提示用户
    if not os.path.exists(corrected_path):
        parent = dialog_parent or parent_window
        themed_message(
            parent, t("k_title_warning"), f"节点文件夹不存在！\n\n路径: {corrected_path}\n\n"
            f"可能原因：\n"
            f"1. 节点已被删除\n"
            f"2. 项目路径已更改\n"
            f"3. 节点数据未正确加载\n\n"
            f"请尝试刷新节点列表。"
        , "warning")
        return False

    # 4. 打开文件夹
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.Popen(['explorer', corrected_path])
        elif system == "Darwin":
            subprocess.Popen(['open', corrected_path])
        else:
            subprocess.Popen(['xdg-open', corrected_path])
        logger.info("[file_utils] 已打开文件夹: %s", corrected_path)
        return True
    except Exception as e:
        logger.error("[file_utils] 打开文件夹失败: %s", e)
        if dialog_parent:
            themed_message(dialog_parent, t("k_title_error"), t("_k_folder_open_fail").format(err=e), "error")
        return False

"""
通用文件工具 — 消除 node_list_panel 和 property_panel 中的重复代码
"""
import os
import subprocess
import platform
import sys
from PyQt6.QtWidgets import QMessageBox
from ui.core.utils.dialog_utils import themed_message
from ui.core.logger import logger
from ui.core.i18n import t


def get_project_root():
    """获取当前项目根目录
    
    Returns:
        str: 项目根目录的绝对路径
    """
    # 从当前文件位置向上查找，直到找到包含特定文件的目录
    current_path = os.path.dirname(os.path.abspath(__file__))
    
    while current_path != os.path.dirname(current_path):
        # 检查是否是项目根目录（通过查找关键文件）
        if (os.path.exists(os.path.join(current_path, "main.py")) or
            os.path.exists(os.path.join(current_path, "README.md")) or
            os.path.exists(os.path.join(current_path, "launcher.py")) or
            os.path.exists(os.path.join(current_path, "nodes"))):
            return current_path
        
        current_path = os.path.dirname(current_path)
    
    # 如果没找到，回退到当前工作目录
    return os.getcwd()


def open_terminal_in_directory(directory, terminal_type="default", dialog_parent=None):
    """在指定目录中打开终端
    
    Args:
        directory: 要在其中打开终端的目录路径
        terminal_type: 终端类型（"default", "powershell", "cmd"）
        dialog_parent: 对话框父窗口，用于显示错误信息
    
    Returns:
        bool: 是否成功打开
    """
    try:
        system = platform.system()
        directory = os.path.normpath(os.path.abspath(directory))
        
        if not os.path.exists(directory):
            if dialog_parent:
                themed_message(dialog_parent, t("k_title_warning"), 
                    f"目录不存在: {directory}", "warning")
            return False
        
        if system == "Windows":
            # 标准化路径格式
            norm_dir = os.path.normpath(directory)
            
            if terminal_type == "powershell":
                # 使用 PowerShell
                ps_cmd = f'Set-Location -LiteralPath \'{norm_dir}\''
                subprocess.Popen(['powershell.exe', '-NoExit', '-Command', ps_cmd],
                    creationflags=subprocess.CREATE_NEW_CONSOLE)
            elif terminal_type == "cmd":
                # 使用 Cmd - 直接构建完整的命令字符串让系统处理
                import shlex
                cmd_command = f'cmd.exe /k "cd /d \"{norm_dir}\""'
                subprocess.Popen(cmd_command,
                    shell=True,
                    creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                # 默认使用 PowerShell
                ps_cmd = f'Set-Location -LiteralPath \'{norm_dir}\''
                subprocess.Popen(['powershell.exe', '-NoExit', '-Command', ps_cmd],
                    creationflags=subprocess.CREATE_NEW_CONSOLE)
        elif system == "Darwin":  # macOS
            # 使用 macOS Terminal
            script = f'''tell application "Terminal"
                do script "cd '{directory}'"
            end tell'''
            subprocess.Popen(['osascript', '-e', script])
        else:  # Linux
            # 尝试常见的终端模拟器
            terminals = ['gnome-terminal', 'konsole', 'xterm', 'xfce4-terminal', 'lxterminal']
            opened = False
            for terminal in terminals:
                try:
                    subprocess.Popen([terminal, '--working-directory', directory])
                    opened = True
                    break
                except Exception:
                    continue
            if not opened:
                if dialog_parent:
                    themed_message(dialog_parent, t("k_title_error"), 
                        "未找到可用的终端模拟器", "error")
                return False
        
        logger.info("[file_utils] 已在目录中打开终端: %s", directory)
        return True
    except Exception as e:
        logger.error("[file_utils] 打开终端失败: %s", e)
        if dialog_parent:
            themed_message(dialog_parent, t("k_title_error"), 
                t("_k_terminal_open_fail").format(err=str(e)), "error")
        return False


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

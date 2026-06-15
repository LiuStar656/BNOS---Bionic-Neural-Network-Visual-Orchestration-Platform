"""
BNOS 导入导出管理器 - 负责节点和项目的导出/导入操作
"""
import os
import shutil
import tempfile
import json
import sys
from PySide6.QtWidgets import QMessageBox
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.packager import Packager
from ui.core.utils.dialog_utils import themed_message, pick_file, pick_save_file


def _repair_portable_venv(node_dir):
    """节点导入后修复 venv，使其在新机器上可运行（Python 3.11+ Windows 相对路径支持）

    修复内容：
    1. pyvenv.cfg 的 home 指向当前机器的 Python 安装目录
    2. start.json 去除绝对 path / python_exe 字段，由运行时动态推断
    """
    venv_dir = os.path.join(node_dir, "venv")
    if not os.path.isdir(venv_dir):
        return

    # 1. 定位当前机器上的 Python（即运行 BNOS 的 Python）
    host_python_exe = sys.executable
    host_python_dir = os.path.dirname(host_python_exe)

    # 2. 重写 pyvenv.cfg：home → 当前 Python 目录，保留 version 信息
    cfg_path = os.path.join(venv_dir, "pyvenv.cfg")
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("home ="):
                    new_lines.append(f"home = {host_python_dir}\n")
                else:
                    new_lines.append(line)

            with open(cfg_path, "w", encoding="utf-8", newline="") as f:
                f.writelines(new_lines)
            logger.info(f"[portable-venv] 已修复 pyvenv.cfg: home → {host_python_dir}")
        except Exception as e:
            logger.warning(f"[portable-venv] 修复 pyvenv.cfg 失败: {e}")

    # 3. 清理 start.json：删除写入时带入的绝对路径（老版本节点兼容处理）
    start_json_path = os.path.join(node_dir, "start.json")
    if os.path.isfile(start_json_path):
        try:
            with open(start_json_path, "r", encoding="utf-8") as f:
                start_cfg = json.load(f)

            modified = False
            if "nodes" in start_cfg and isinstance(start_cfg["nodes"], list):
                for node in start_cfg["nodes"]:
                    if isinstance(node, dict):
                        if "python_exe" in node:
                            del node["python_exe"]
                            modified = True
                        if "path" in node and os.path.isabs(str(node["path"])):
                            del node["path"]
                            modified = True

            if modified:
                with open(start_json_path, "w", encoding="utf-8") as f:
                    json.dump(start_cfg, f, indent=2, ensure_ascii=False)
                logger.info("[portable-venv] 已清理 start.json 中的绝对路径")
        except Exception as e:
            logger.warning(f"[portable-venv] 清理 start.json 失败: {e}")


class ImportExportManager:
    """导入导出管理器"""
    
    def __init__(self, main_window):
        self.main_window = main_window
    
    def export_node(self, node_name):
        """
        导出单个节点为 .bnos 文件
        
        Args:
            node_name (str): 要导出的节点名称
        
        Returns:
            bool: 是否导出成功
        """
        try:
            # 获取节点信息
            if node_name not in self.main_window.nodes_data:
                themed_message(self.main_window, t("k_title_error"), 
                              f"节点 '{node_name}' 不存在", "error")
                return False
            
            node_info = self.main_window.nodes_data[node_name]
            node_path = node_info['path']
            
            if not os.path.isdir(node_path):
                themed_message(self.main_window, t("k_title_error"), 
                              f"节点目录不存在: {node_path}", "error")
                return False
            
            # 使用自绘文件保存对话框
            file_path = pick_save_file(
                self.main_window,
                t("k_export_node"),
                default_name=node_name,
                filter_ext=Packager.BNOS_EXTENSION
            )
            
            if not file_path:
                return False
            
            # 压缩节点目录
            result = Packager.compress_directory(node_path, file_path[:-len(Packager.BNOS_EXTENSION)], Packager.BNOS_EXTENSION)
            
            if result:
                themed_message(self.main_window, t("k_title_success"), 
                              f"节点 '{node_name}' 已导出到:\n{result}", "success")
                return True
            else:
                themed_message(self.main_window, t("k_title_error"), 
                              f"导出节点 '{node_name}' 失败", "error")
                return False
                
        except Exception as e:
            logger.error(f"导出节点失败: {e}")
            themed_message(self.main_window, t("k_title_error"), 
                          f"导出节点失败: {str(e)}", "error")
            return False
    
    def export_project(self):
        """
        导出整个项目为 .bnosc 文件
        
        Returns:
            bool: 是否导出成功
        """
        try:
            if not self.main_window.current_project_path:
                themed_message(self.main_window, t("k_title_warning"), 
                              t("k_project_no_project"), "warning")
                return False
            
            project_path = self.main_window.current_project_path
            project_name = os.path.basename(project_path)
            
            # 使用自绘文件保存对话框
            file_path = pick_save_file(
                self.main_window,
                t("k_export_project"),
                default_name=project_name,
                filter_ext=Packager.BNOSC_EXTENSION
            )
            
            if not file_path:
                return False
            
            # 压缩项目目录
            result = Packager.compress_directory(project_path, file_path[:-len(Packager.BNOSC_EXTENSION)], Packager.BNOSC_EXTENSION)
            
            if result:
                themed_message(self.main_window, t("k_title_success"), 
                              f"项目已导出到:\n{result}", "success")
                return True
            else:
                themed_message(self.main_window, t("k_title_error"), 
                              "导出项目失败", "error")
                return False
                
        except Exception as e:
            logger.error(f"导出项目失败: {e}")
            themed_message(self.main_window, t("k_title_error"), 
                          f"导出项目失败: {str(e)}", "error")
            return False
    
    def import_node(self):
        """
        导入 .bnos 节点包
        
        Returns:
            bool: 是否导入成功
        """
        try:
            if not self.main_window.current_project_path:
                themed_message(self.main_window, t("k_title_warning"), 
                              t("k_project_no_project"), "warning")
                return False
            
            # 使用自绘文件选择对话框
            file_path = pick_file(
                self.main_window,
                t("k_import_node"),
                filter_ext=Packager.BNOS_EXTENSION
            )
            
            if not file_path:
                return False
            
            # 验证文件格式
            if not Packager.validate_bnos_package(file_path):
                themed_message(self.main_window, t("k_title_error"), 
                              "无效的节点包格式", "error")
                return False
            
            # 解压到临时目录
            temp_dir = tempfile.mkdtemp()
            extracted_dir = Packager.extract_package(file_path, temp_dir)
            
            if not extracted_dir:
                shutil.rmtree(temp_dir)
                themed_message(self.main_window, t("k_title_error"), 
                              "解压节点包失败", "error")
                return False
            
            # 获取节点名称
            node_name = os.path.basename(extracted_dir)
            
            # 检查目标位置是否已存在
            nodes_dir = os.path.join(self.main_window.current_project_path, "nodes")
            target_path = os.path.join(nodes_dir, node_name)
            
            if os.path.exists(target_path):
                reply = QMessageBox.question(
                    self.main_window,
                    t("k_title_warning"),
                    f"节点 '{node_name}' 已存在，是否覆盖？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    # 尝试重命名
                    counter = 1
                    while os.path.exists(target_path):
                        new_name = f"{node_name}_{counter}"
                        target_path = os.path.join(nodes_dir, new_name)
                        counter += 1
                    node_name = new_name
            
            # 移动到目标位置
            shutil.move(extracted_dir, target_path)
            # 只有当临时目录与解压目录不同时才删除临时目录
            if temp_dir != extracted_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            # 修复 venv 的路径硬编码，使其在新机器上可运行
            _repair_portable_venv(target_path)
            
            # 刷新节点列表
            self.main_window.refresh_nodes()
            
            themed_message(self.main_window, t("k_title_success"), 
                          f"节点 '{node_name}' 已导入", "success")
            return True
                
        except Exception as e:
            logger.error(f"导入节点失败: {e}")
            themed_message(self.main_window, t("k_title_error"), 
                          f"导入节点失败: {str(e)}", "error")
            return False
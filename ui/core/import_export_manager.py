"""
BNOS 导入导出管理器 - 负责节点和项目的导出/导入操作
"""
import os
import shutil
import tempfile
from PyQt6.QtWidgets import QMessageBox
from ui.core.logger import logger
from ui.core.i18n import t
from ui.core.packager import Packager
from ui.core.utils.dialog_utils import themed_message, pick_file, pick_save_file


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
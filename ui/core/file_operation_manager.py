"""
文件操作管理器 - 处理文件复制、删除、重命名等操作
"""
import os
import shutil
import threading
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from ui.core.logger import logger


class FileOperationManager(QObject):
    """文件操作管理器"""
    
    # 信号定义
    operation_started = pyqtSignal(str)  # 操作开始
    operation_progress = pyqtSignal(int)  # 进度更新 (0-100)
    operation_completed = pyqtSignal(str, bool)  # 操作完成 (操作类型, 是否成功)
    operation_error = pyqtSignal(str, str)  # 操作错误 (操作类型, 错误信息)
    
    def __init__(self):
        super().__init__()
        self._is_running = False
        self._cancel_event = threading.Event()
    
    @pyqtSlot(str, str)
    def copy_file(self, source_path, dest_path):
        """复制文件或目录"""
        if self._is_running:
            self.operation_error.emit('copy', 'Another operation is running')
            return
        
        self._is_running = True
        self._cancel_event.clear()
        
        def _copy():
            try:
                self.operation_started.emit('copy')
                
                if os.path.isdir(source_path):
                    # 复制目录
                    if os.path.exists(dest_path):
                        dest_path = self._get_unique_path(dest_path)
                    
                    total_size = self._get_directory_size(source_path)
                    copied_size = 0
                    
                    shutil.copytree(source_path, dest_path)
                    self.operation_progress.emit(100)
                else:
                    # 复制文件
                    if os.path.exists(dest_path):
                        dest_path = self._get_unique_path(dest_path)
                    
                    shutil.copy2(source_path, dest_path)
                    self.operation_progress.emit(100)
                
                self.operation_completed.emit('copy', True)
                
            except Exception as e:
                logger.error(f"Copy failed: {e}")
                self.operation_error.emit('copy', str(e))
                self.operation_completed.emit('copy', False)
            finally:
                self._is_running = False
        
        thread = threading.Thread(target=_copy)
        thread.start()
    
    @pyqtSlot(str)
    def delete_file(self, path):
        """删除文件或目录"""
        if self._is_running:
            self.operation_error.emit('delete', 'Another operation is running')
            return
        
        self._is_running = True
        
        def _delete():
            try:
                self.operation_started.emit('delete')
                
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                
                self.operation_progress.emit(100)
                self.operation_completed.emit('delete', True)
                
            except Exception as e:
                logger.error(f"Delete failed: {e}")
                self.operation_error.emit('delete', str(e))
                self.operation_completed.emit('delete', False)
            finally:
                self._is_running = False
        
        thread = threading.Thread(target=_delete)
        thread.start()
    
    @pyqtSlot(str, str)
    def rename_file(self, old_path, new_name):
        """重命名文件或目录"""
        if self._is_running:
            self.operation_error.emit('rename', 'Another operation is running')
            return
        
        self._is_running = True
        
        def _rename():
            try:
                self.operation_started.emit('rename')
                
                new_path = os.path.join(os.path.dirname(old_path), new_name)
                
                # 检查目标是否存在
                if os.path.exists(new_path):
                    new_path = self._get_unique_path(new_path)
                
                os.rename(old_path, new_path)
                
                self.operation_progress.emit(100)
                self.operation_completed.emit('rename', True)
                
            except Exception as e:
                logger.error(f"Rename failed: {e}")
                self.operation_error.emit('rename', str(e))
                self.operation_completed.emit('rename', False)
            finally:
                self._is_running = False
        
        thread = threading.Thread(target=_rename)
        thread.start()
    
    @pyqtSlot(str)
    def create_folder(self, parent_path, name=None):
        """创建新文件夹"""
        if self._is_running:
            self.operation_error.emit('create_folder', 'Another operation is running')
            return
        
        self._is_running = True
        
        def _create():
            try:
                self.operation_started.emit('create_folder')
                
                if not name:
                    name = 'New Folder'
                
                new_path = os.path.join(parent_path, name)
                
                # 检查是否已存在
                counter = 1
                while os.path.exists(new_path):
                    new_path = os.path.join(parent_path, f'{name} ({counter})')
                    counter += 1
                
                os.makedirs(new_path)
                
                self.operation_progress.emit(100)
                self.operation_completed.emit('create_folder', True)
                
            except Exception as e:
                logger.error(f"Create folder failed: {e}")
                self.operation_error.emit('create_folder', str(e))
                self.operation_completed.emit('create_folder', False)
            finally:
                self._is_running = False
        
        thread = threading.Thread(target=_create)
        thread.start()
    
    def cancel_operation(self):
        """取消当前操作"""
        self._cancel_event.set()
    
    def is_running(self):
        """检查是否有操作正在进行"""
        return self._is_running
    
    def _get_unique_path(self, path):
        """获取唯一路径（如果已存在则添加数字后缀）"""
        if not os.path.exists(path):
            return path
        
        dir_name = os.path.dirname(path)
        base_name = os.path.basename(path)
        
        # 分离文件名和扩展名
        if '.' in base_name:
            name, ext = os.path.splitext(base_name)
        else:
            name, ext = base_name, ''
        
        counter = 1
        new_path = os.path.join(dir_name, f'{name} ({counter}){ext}')
        
        while os.path.exists(new_path):
            counter += 1
            new_path = os.path.join(dir_name, f'{name} ({counter}){ext}')
        
        return new_path
    
    def _get_directory_size(self, path):
        """获取目录大小"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.exists(fp):
                    total_size += os.path.getsize(fp)
        return total_size


# 全局文件操作管理器实例
file_operation_manager = FileOperationManager()
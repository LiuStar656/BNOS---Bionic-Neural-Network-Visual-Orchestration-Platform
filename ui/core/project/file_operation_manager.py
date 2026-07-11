"""
文件操作管理器 - 处理文件复制、删除、重命名等操作
"""

from __future__ import annotations

import shutil
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from ui.core.logger import logger


class FileOperationManager(QObject):
    """文件操作管理器"""

    # 信号定义
    operation_started = Signal(str)  # 操作开始
    operation_progress = Signal(int)  # 进度更新 (0-100)
    operation_completed = Signal(str, bool)  # 操作完成 (操作类型, 是否成功)
    operation_error = Signal(str, str)  # 操作错误 (操作类型, 错误信息)

    def __init__(self):
        super().__init__()
        self._is_running = False
        self._cancel_event = threading.Event()
        self._lock = threading.Lock()  # R04: 保护 _is_running 的 check-then-act

    @Slot(str, str)
    def copy_file(self, source_path, dest_path):
        """复制文件或目录"""
        with self._lock:  # R04
            if self._is_running:
                self.operation_error.emit("copy", "Another operation is running")
                return
            self._is_running = True
        self._cancel_event.clear()

        def _copy():
            try:
                self.operation_started.emit("copy")

                source = Path(source_path)
                dest = Path(dest_path)

                if source.is_dir():
                    # 复制目录
                    if dest.exists():
                        dest = self._get_unique_path(dest)

                    self._get_directory_size(source_path)

                    shutil.copytree(str(source), str(dest))
                    self.operation_progress.emit(100)
                else:
                    # 复制文件
                    if dest.exists():
                        dest = self._get_unique_path(dest)

                    shutil.copy2(str(source), str(dest))
                    self.operation_progress.emit(100)

                self.operation_completed.emit("copy", True)

            except Exception as e:
                logger.error(f"Copy failed: {e}")
                self.operation_error.emit("copy", str(e))
                self.operation_completed.emit("copy", False)
            finally:
                with self._lock:  # R04
                    self._is_running = False

        thread = threading.Thread(target=_copy)
        thread.start()

    @Slot(str)
    def delete_file(self, path):
        """删除文件或目录"""
        with self._lock:  # R04
            if self._is_running:
                self.operation_error.emit("delete", "Another operation is running")
                return
            self._is_running = True

        def _delete():
            try:
                self.operation_started.emit("delete")

                p = Path(path)

                if p.is_dir():
                    shutil.rmtree(str(p))
                else:
                    p.unlink()

                self.operation_progress.emit(100)
                self.operation_completed.emit("delete", True)

            except Exception as e:
                logger.error(f"Delete failed: {e}")
                self.operation_error.emit("delete", str(e))
                self.operation_completed.emit("delete", False)
            finally:
                with self._lock:  # R04
                    self._is_running = False

        thread = threading.Thread(target=_delete)
        thread.start()

    @Slot(str, str)
    def rename_file(self, old_path, new_name):
        """重命名文件或目录"""
        with self._lock:  # R04
            if self._is_running:
                self.operation_error.emit("rename", "Another operation is running")
                return
            self._is_running = True

        def _rename():
            try:
                self.operation_started.emit("rename")

                old = Path(old_path)
                new_path = old.parent / new_name

                # 检查目标是否存在
                if new_path.exists():
                    new_path = self._get_unique_path(new_path)

                old.rename(new_path)

                self.operation_progress.emit(100)
                self.operation_completed.emit("rename", True)

            except Exception as e:
                logger.error(f"Rename failed: {e}")
                self.operation_error.emit("rename", str(e))
                self.operation_completed.emit("rename", False)
            finally:
                with self._lock:  # R04
                    self._is_running = False

        thread = threading.Thread(target=_rename)
        thread.start()

    @Slot(str)
    def create_folder(self, parent_path, name=None):
        """创建新文件夹"""
        with self._lock:  # R04
            if self._is_running:
                self.operation_error.emit("create_folder", "Another operation is running")
                return
            self._is_running = True

        def _create():
            try:
                self.operation_started.emit("create_folder")

                if not name:  # noqa: F823
                    name = "New Folder"

                parent = Path(parent_path)
                new_path = parent / name

                # 检查是否已存在
                counter = 1
                while new_path.exists():
                    new_path = parent / f"{name} ({counter})"
                    counter += 1

                new_path.mkdir(parents=True)

                self.operation_progress.emit(100)
                self.operation_completed.emit("create_folder", True)

            except Exception as e:
                logger.error(f"Create folder failed: {e}")
                self.operation_error.emit("create_folder", str(e))
                self.operation_completed.emit("create_folder", False)
            finally:
                with self._lock:  # R04
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
        path = Path(path)
        if not path.exists():
            return path

        parent = path.parent
        stem = path.stem
        suffix = path.suffix

        counter = 1
        new_path = parent / f"{stem} ({counter}){suffix}"

        while new_path.exists():
            counter += 1
            new_path = parent / f"{stem} ({counter}){suffix}"

        return new_path

    def _get_directory_size(self, path):
        """获取目录大小"""
        total_size = 0
        for entry in Path(path).rglob("*"):
            if entry.is_file():
                total_size += entry.stat().st_size
        return total_size


# 全局文件操作管理器实例
file_operation_manager = FileOperationManager()

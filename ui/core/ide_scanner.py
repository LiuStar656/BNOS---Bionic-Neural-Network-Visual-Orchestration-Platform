"""
IDE 自动扫描器 — 自动检测 VSCode / Trae IDE + 统一的打开逻辑
跨平台：Windows / Linux / macOS
（菜单构建由 Action 系统负责，此模块只提供检测和打开能力）
"""
import json
import os
import sys
import shutil
import subprocess
from typing import Optional, Dict

from PyQt6.QtWidgets import QPushButton, QMessageBox

from ui.core.i18n import t


class IDEScanner:
    """IDE 自动扫描器 — 扫描系统安装路径 + 命令行 PATH 双重检测"""

    _CACHE_KEY_VSCODE = "ide_vscode_path"
    _CACHE_KEY_TRAE = "ide_trae_path"

    # ── Windows 扫描路径 ──
    _VSCODE_WIN_PATHS = [
        r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe",
        r"%PROGRAMFILES%\Microsoft VS Code\Code.exe",
        r"%PROGRAMFILES(x86)%\Microsoft VS Code\Code.exe",
        os.path.expanduser(r"~\scoop\apps\vscode\current\Code.exe"),
    ]

    _TRAE_WIN_PATHS = [
        r"%LOCALAPPDATA%\Programs\Trae CN\Trae CN.exe",
        r"%LOCALAPPDATA%\Programs\Trae CN\resources\app\bin\trae.cmd",
        r"%LOCALAPPDATA%\Programs\Trae\Trae.exe",
        os.path.expanduser(r"~\scoop\apps\trae\current\Trae.exe"),
    ]

    # ── Linux 扫描路径 ──
    _VSCODE_LINUX_PATHS = [
        "/usr/bin/code", "/usr/local/bin/code", "/snap/bin/code",
        os.path.expanduser("~/.local/bin/code"),
    ]

    _TRAE_LINUX_PATHS = [
        os.path.expanduser("~/.local/share/trae/trae"),
        os.path.expanduser("~/.local/bin/trae"), "/usr/local/bin/trae",
    ]

    # ── macOS 扫描路径 ──
    _VSCODE_MACOS_PATHS = [
        "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
        os.path.expanduser("~/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code"),
    ]

    _TRAE_MACOS_PATHS = [
        "/Applications/Trae.app/Contents/MacOS/Trae",
        "/Applications/Trae CN.app/Contents/MacOS/Trae CN",
    ]

    def __init__(self, app_config=None):
        self._app_config = app_config
        self._cache: Dict[str, Optional[str]] = {}
        self._load_cache()

    # ========================================================================
    #  公开 API — 查找 IDE
    # ========================================================================

    def find_vscode(self) -> Optional[str]:
        return self._find("vscode", self._CACHE_KEY_VSCODE, self._get_vscode_scan_paths())

    def find_trae_ide(self) -> Optional[str]:
        return self._find("trae", self._CACHE_KEY_TRAE, self._get_trae_scan_paths())

    # ========================================================================
    #  公开 API — 打开（供 Action + 对话框按钮共用）
    # ========================================================================

    def open_vscode_workspace(self, node_name: str, node_path: str) -> bool:
        """生成 .code-workspace 文件后用 VSCode 打开节点目录"""
        workspace_file = os.path.join(node_path, f"{node_name}.code-workspace")
        py_exe = "${workspaceFolder}/venv/Scripts/python.exe" if sys.platform == "win32" else "${workspaceFolder}/venv/bin/python"
        config = {
            "folders": [{"path": "."}],
            "settings": {
                "python.defaultInterpreterPath": py_exe,
                "files.exclude": {"**/__pycache__": True, "**/*.pyc": True}
            }
        }
        with open(workspace_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        if self.open_in_vscode(workspace_file):
            return True
        self._show_not_found("VSCode")
        return False

    def open_in_vscode(self, workspace_path: str) -> bool:
        exe = self.find_vscode()
        return self._spawn(exe, workspace_path) if exe else False

    def open_in_trae(self, workspace_path: str) -> bool:
        exe = self.find_trae_ide()
        if exe and self._spawn(exe, workspace_path):
            return True
        self._show_not_found("Trae IDE")
        return False

    def open_in_ide(self, workspace_path: str, ide_type: str = "vscode") -> bool:
        if ide_type == "trae":
            return self.open_in_trae(workspace_path)
        return self.open_in_vscode(workspace_path)

    # ========================================================================
    #  公开 API — 对话框按钮（不属于右键菜单，保留 UI 构建）
    # ========================================================================

    def add_buttons_to_layout(self, layout, node_name: str, node_path: str):
        """向 QVBoxLayout / QHBoxLayout 添加 IDE 打开按钮（对话框专用）"""
        vscode_btn = QPushButton(t("k_open_vscode"))
        vscode_btn.setStyleSheet("background-color: #666666; color: white; padding: 10px;")
        vscode_btn.clicked.connect(lambda: self.open_vscode_workspace(node_name, node_path))
        layout.addWidget(vscode_btn)

        trae_btn = QPushButton(t("_k_open_trae"))
        trae_btn.setStyleSheet("background-color: #6a9955; color: white; padding: 10px;")
        trae_btn.clicked.connect(lambda: self.open_in_trae(node_path))
        layout.addWidget(trae_btn)

    # ========================================================================
    #  内部 — 查找逻辑
    # ========================================================================

    def _find(self, name: str, cache_key: str, scan_paths: list) -> Optional[str]:
        """统一查找：内存缓存 → app_config → PATH 命令 → 进程/环境变量 → 文件系统"""
        if name in self._cache:
            cached = self._cache[name]
            if cached and os.path.exists(cached): return cached
        if self._app_config:
            cached = self._app_config.get(cache_key)
            if cached and os.path.exists(cached):
                self._cache[name] = cached
                self._app_config.set(cache_key, cached)
                self._app_config.save()
                return cached
        result = self._check_path_command(name)
        if result: self._save_result(name, cache_key, result); return result
        result = self._find_from_runtime(name)
        if result: self._save_result(name, cache_key, result); return result
        for raw_path in scan_paths:
            expanded = os.path.expandvars(raw_path) if '%' in raw_path else raw_path
            expanded = os.path.expanduser(expanded)
            if os.path.exists(expanded):
                self._save_result(name, cache_key, expanded); return expanded
        return None

    def _find_from_runtime(self, name: str) -> Optional[str]:
        """从环境变量 / 运行中进程检测 IDE 路径（覆盖非标准安装位置）"""
        if sys.platform != 'win32':
            return None
        if name == "trae":
            # 1) 从 Trae sandbox 环境变量推导
            sandbox_path = os.environ.get('TRAE_SANDBOX_CLI_PATH', '')
            if sandbox_path and os.path.exists(sandbox_path):
                # F:\Trae CN\resources\app\modules\sandbox\trae-sandbox.exe
                # → 向上 5 级 → F:\Trae CN
                trae_root = sandbox_path
                for _ in range(5):
                    trae_root = os.path.dirname(trae_root)
                for candidate in [os.path.join(trae_root, 'Trae CN.exe'),
                                  os.path.join(trae_root, 'Trae.exe')]:
                    if os.path.exists(candidate):
                        return candidate
            # 2) 从运行中进程查找
            exe = self._find_process_exe("Trae CN")
            if exe: return exe
            exe = self._find_process_exe("Trae")
            if exe: return exe
        return None

    @staticmethod
    def _find_process_exe(process_name: str) -> Optional[str]:
        """通过 PowerShell 查找运行中进程的可执行文件路径"""
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command',
                 f'(Get-Process -Name "{process_name}" -ErrorAction SilentlyContinue | Select-Object -First 1).Path'],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode == 0:
                path = result.stdout.strip()
                if path and os.path.exists(path):
                    return path
        except Exception:
            pass
        return None

    def _check_path_command(self, name: str) -> Optional[str]:
        if name == "vscode": command = "code"
        else: command = "trae"
        binary = shutil.which(command)
        if binary: return binary
        if sys.platform == 'win32' and name == "vscode":
            try:
                result = subprocess.run(
                    ['where', 'code'], capture_output=True, text=True, timeout=3,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if lines and lines[0].strip(): return lines[0].strip()
            except Exception: pass
        return None

    def _save_result(self, name: str, cache_key: str, path: str):
        self._cache[name] = path
        if self._app_config:
            self._app_config.set(cache_key, path)
            self._app_config.save()

    def _load_cache(self):
        if self._app_config:
            vscode = self._app_config.get(self._CACHE_KEY_VSCODE)
            trae = self._app_config.get(self._CACHE_KEY_TRAE)
            if vscode and os.path.exists(vscode): self._cache["vscode"] = vscode
            if trae and os.path.exists(trae): self._cache["trae"] = trae

    def _get_vscode_scan_paths(self) -> list:
        if sys.platform == 'win32': return self._VSCODE_WIN_PATHS
        elif sys.platform == 'darwin': return self._VSCODE_MACOS_PATHS
        return self._VSCODE_LINUX_PATHS

    def _get_trae_scan_paths(self) -> list:
        if sys.platform == 'win32': return self._TRAE_WIN_PATHS
        elif sys.platform == 'darwin': return self._TRAE_MACOS_PATHS
        return self._TRAE_LINUX_PATHS

    # ========================================================================
    #  内部 — 进程启动 + 错误提示
    # ========================================================================

    def _spawn(self, exe: str, path: str) -> bool:
        try:
            kwargs = dict(shell=False)
            if sys.platform == 'win32': kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            subprocess.Popen([exe, path], **kwargs)
            return True
        except Exception: return False

    @staticmethod
    def _show_not_found(ide_name: str):
        QMessageBox.information(None, ide_name,
            f"未找到 {ide_name} 安装\n\n请确保已安装 {ide_name}。")


# 全局单例
ide_scanner = IDEScanner()

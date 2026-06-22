"""
应用配置管理 - 全局配置记忆系统

统一配置系统，支持：
- 窗口几何、分割器比例、最后项目等基础配置
- 主题配置（深色/浅色模式、颜色方案）
- 布局配置（面板位置、可见性、工具栏状态）
- 快捷键配置（自定义快捷键）
- 轮询频率配置

使用单例模式确保全局只有一个配置实例
"""
import os
import json
from typing import Dict, Any
from ui.core.logger import logger


class AppConfig:
    """应用配置管理 - 单例模式"""
    
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppConfig, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.config_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..",
            "app_config.json"
        )

        self.config = {
            "window_geometry": {
                "x": 100, "y": 100, "width": 1400, "height": 900,
                "maximized": False
            },
            "splitter_sizes": [250, 1150],
            "last_project": None,
            "canvas_view_state": {
                "scale": 1.0, "scroll_x": 0, "scroll_y": 0
            },
            "language": "cn",
            "process_mode": False,
            "draw_toolbar_visible": False,
            "rendering": {
                "canvas_width": 5000,
                "canvas_height": 5000,
                "antialiasing": True
            },
            "panel_positions": {
                "node_list_floating": {"x": 10, "y": 100},
                "resource_monitor_floating": {"x": 10, "y": 100},
                "node_monitor_floating": {"x": 10, "y": 100},
                "node_list_dock": {"x": 0, "y": 0},
                "resource_monitor_dock": {"x": 0, "y": 0},
                "node_monitor_dock": {"x": 0, "y": 0},
                "terminal_dock": {"x": 0, "y": 0}
            },
            "panel_visibility": {
                "node_list": False,
                "resource_monitor": False,
                "node_monitor": False,
                "node_list_dock": False,
                "resource_monitor_dock": False,
                "node_monitor_dock": False,
                "node_list_floating": False,
                "resource_monitor_floating": False,
                "node_monitor_floating": False,
                "terminal_dock": False
            },

            "theme": {
                "mode": "dark",
                "accent_color": "#00D4FF",
                "primary_color": "#252526",
                "secondary_color": "#1E1E1E",
                "text_color": "#FFFFFF",
                "text_color_secondary": "#A0A0A0",
                "border_color": "#3C3C3C",
                "canvas_bg": "#1E1E1E",
                "canvas_grid": "#2A2A2A",
                "node_bg": "#2D2D2D",
                "node_border": "#3C3C3C",
                "node_selected_border": "#00D4FF",
                "edge_color": "#666666",
                "edge_selected_color": "#00D4FF",
                "success_color": "#00FF88",
                "warning_color": "#FFAA00",
                "error_color": "#FF4444",
                "info_color": "#00D4FF"
            },

            "layout": {
                "panel_layout": "left",
                "toolbar_position": "top",
                "status_bar_visible": True,
                "tab_bar_visible": True,
                "auto_hide_panels": False,
                "panel_width": 250
            },

            "shortcuts": {
                "undo": "Ctrl+Z",
                "redo": "Ctrl+Y",
                "cut": "Ctrl+X",
                "copy": "Ctrl+C",
                "paste": "Ctrl+V",
                "delete": "Delete",
                "select_all": "Ctrl+A",
                "save": "Ctrl+S",
                "open": "Ctrl+O",
                "new": "Ctrl+N",
                "close": "Ctrl+W",
                "zoom_in": "Ctrl++",
                "zoom_out": "Ctrl+-",
                "zoom_reset": "Ctrl+0",
                "run": "F5",
                "stop": "F6",
                "debug": "F9",
                "toggle_panel": "Ctrl+Shift+P",
                "toggle_terminal": "Ctrl+`",
                "find": "Ctrl+F",
                "replace": "Ctrl+H"
            },

            "performance": {
                "polling_frequency": 2,
                "dynamic_frequency": True,
                "cpu_low_threshold": 30,
                "cpu_high_threshold": 60,
                "render_caching": True,
                "viewport_clipping": True
            }
        }

        self.load()
        self._initialized = True

    def load(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                for key in loaded:
                    if key in self.config and isinstance(self.config[key], dict) and isinstance(loaded[key], dict):
                        self.config[key].update(loaded[key])
                    else:
                        self.config[key] = loaded[key]
                logger.info("配置已加载: %s", self.config_file)
            else:
                logger.info("配置文件不存在，使用默认配置")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("配置文件损坏，重置: %s", e)
            if os.path.exists(self.config_file):
                try:
                    import shutil
                    shutil.copy2(self.config_file, self.config_file + ".bak")
                except Exception:
                    pass
        except Exception as e:
            logger.error("加载配置失败: %s", e)

    def save(self):
        tmp_path = self.config_file + ".tmp"
        bak_path = self.config_file + ".bak"
        
        try:
            d = os.path.dirname(self.config_file)
            if not os.path.exists(d):
                os.makedirs(d)
            
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            if os.path.exists(self.config_file):
                os.replace(self.config_file, bak_path)
            
            os.replace(tmp_path, self.config_file)
            
            if os.path.exists(bak_path):
                os.remove(bak_path)
            
            logger.info("配置已保存: %s", self.config_file)
        except Exception as e:
            if os.path.exists(bak_path):
                os.replace(bak_path, self.config_file)
            logger.error("保存配置失败: %s", e)
            raise e

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value

    def get_theme(self, key=None, default=None):
        """获取主题配置"""
        if key is None:
            return self.config.get("theme", {})
        return self.config.get("theme", {}).get(key, default)

    def set_theme(self, key, value):
        """设置主题配置"""
        self.config["theme"][key] = value

    def get_layout(self, key=None, default=None):
        """获取布局配置"""
        if key is None:
            return self.config.get("layout", {})
        return self.config.get("layout", {}).get(key, default)

    def set_layout(self, key, value):
        """设置布局配置"""
        self.config["layout"][key] = value

    def get_shortcut(self, action, default=None):
        """获取快捷键配置"""
        return self.config.get("shortcuts", {}).get(action, default)

    def set_shortcut(self, action, key_sequence):
        """设置快捷键配置"""
        self.config["shortcuts"][action] = key_sequence

    def get_performance(self, key=None, default=None):
        """获取性能配置"""
        if key is None:
            return self.config.get("performance", {})
        return self.config.get("performance", {}).get(key, default)

    def set_performance(self, key, value):
        """设置性能配置"""
        self.config["performance"][key] = value
"""
应用配置管理 - 全局配置记忆系统
负责窗口几何、分割器比例、最后项目等持久化
使用单例模式确保全局只有一个配置实例
"""
import os
import json
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
        try:
            d = os.path.dirname(self.config_file)
            if not os.path.exists(d):
                os.makedirs(d)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info("配置已保存: %s", self.config_file)
        except Exception as e:
            logger.error("保存配置失败: %s", e)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
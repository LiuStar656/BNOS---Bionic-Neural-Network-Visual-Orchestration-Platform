"""
应用配置管理 - 全局配置记忆系统
负责窗口几何、分割器比例、最后项目等持久化
"""
import os
import json
from ui.core.logger import logger


class AppConfig:
    """应用配置管理"""

    def __init__(self):
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
            "process_mode": False
        }

        self.load()

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

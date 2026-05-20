"""
BNOS 应用配置管理 - 全局配置记忆系统

负责：
1. 窗口布局持久化
2. 项目路径记忆
3. 画布视图状态保存
4. Splitter 比例记忆
"""
import os
import json


class AppConfig:
    """应用配置管理 - 全局配置记忆系统"""
    
    def __init__(self):
        # 配置文件路径（程序根目录）
        self.config_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "..", 
            "..", 
            "app_config.json"
        )
        
        # 默认配置
        self.config = {
            # 窗口布局持久化
            "window_geometry": {
                "x": 100,
                "y": 100,
                "width": 1400,
                "height": 900,
                "maximized": False
            },
            "splitter_sizes": [250, 1150],  # 左侧节点列表 + 右侧画布
            
            # 项目记忆
            "last_project": None,
            
            # 画布视图状态（最后的项目）
            "canvas_view_state": {
                "scale": 1.0,
                "scroll_x": 0,
                "scroll_y": 0
            }
        }
        
        # 加载配置
        self.load()
    
    def load(self):
        """加载配置 - 带异常处理"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    
                    # 合并配置（保留新字段的默认值）
                    for key in loaded:
                        if key in self.config:
                            if isinstance(self.config[key], dict) and isinstance(loaded[key], dict):
                                # 字典类型：深度合并
                                self.config[key].update(loaded[key])
                            else:
                                # 其他类型：直接覆盖
                                self.config[key] = loaded[key]
                                
                print(f"✅ 配置已加载: {self.config_file}")
            else:
                print(f"ℹ️  配置文件不存在，使用默认配置")
                
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  配置文件损坏，重置为默认配置: {e}")
            # 备份损坏的文件
            if os.path.exists(self.config_file):
                backup_file = self.config_file + ".bak"
                try:
                    import shutil
                    shutil.copy2(self.config_file, backup_file)
                    print(f"📦 已备份损坏的配置: {backup_file}")
                except:
                    pass
        except Exception as e:
            print(f"❌ 加载配置失败: {e}")
    
    def save(self):
        """保存配置 - 带异常处理"""
        try:
            # 确保目录存在
            config_dir = os.path.dirname(self.config_file)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
                
            print(f"✅ 配置已保存: {self.config_file}")
            
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
    
    def get(self, key, default=None):
        """获取配置项
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        return self.config.get(key, default)
    
    def set(self, key, value):
        """设置配置项
        
        Args:
            key: 配置键
            value: 配置值
        """
        self.config[key] = value
    
    def get_window_geometry(self):
        """获取窗口几何信息
        
        Returns:
            dict: 窗口几何信息
        """
        return self.config.get("window_geometry", {})
    
    def set_window_geometry(self, x, y, width, height, maximized=False):
        """设置窗口几何信息
        
        Args:
            x: X坐标
            y: Y坐标
            width: 宽度
            height: 高度
            maximized: 是否最大化
        """
        self.config["window_geometry"] = {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "maximized": maximized
        }
    
    def get_splitter_sizes(self):
        """获取 Splitter 尺寸
        
        Returns:
            list: Splitter 尺寸列表
        """
        return self.config.get("splitter_sizes", [250, 1150])
    
    def set_splitter_sizes(self, sizes):
        """设置 Splitter 尺寸
        
        Args:
            sizes: Splitter 尺寸列表
        """
        if isinstance(sizes, list) and len(sizes) == 2:
            self.config["splitter_sizes"] = sizes
    
    def get_last_project(self):
        """获取最后打开的项目路径
        
        Returns:
            str: 项目路径或 None
        """
        return self.config.get("last_project")
    
    def set_last_project(self, project_path):
        """设置最后打开的项目路径
        
        Args:
            project_path: 项目路径
        """
        self.config["last_project"] = project_path
    
    def get_canvas_view_state(self):
        """获取画布视图状态
        
        Returns:
            dict: 视图状态
        """
        return self.config.get("canvas_view_state", {})
    
    def set_canvas_view_state(self, scale, scroll_x, scroll_y):
        """设置画布视图状态
        
        Args:
            scale: 缩放比例
            scroll_x: 水平滚动位置
            scroll_y: 垂直滚动位置
        """
        self.config["canvas_view_state"] = {
            "scale": scale,
            "scroll_x": scroll_x,
            "scroll_y": scroll_y
        }

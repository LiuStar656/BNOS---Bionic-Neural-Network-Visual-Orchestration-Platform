"""
BNOS UI 组件包 - 统一入口

模块化结构:
- core/         核心组件（配置、Toast通知）
- menu/         菜单系统
- canvas/       画布系统
- panels/       面板组件
- creators/     节点创建器
- docs/         文档和示例
"""

# 核心组件
from ui.core import AppConfig, ToastNotification, ToastManager

# 菜单系统
from ui.menu import MenuManager

# 画布系统
from ui.canvas import NodeCanvas, NodeItem, EdgeItem, AnchorItem

# 面板组件
from ui.panels import NodeListPanel, NodeConfigDialog, ColorSettingsDialog, NodeGroupManager

# 节点创建器
from ui.creators import NodeCreatorManager

__all__ = [
    # 核心
    'AppConfig',
    'ToastNotification',
    'ToastManager',
    
    # 菜单
    'MenuManager',
    
    # 画布
    'NodeCanvas',
    'NodeItem',
    'EdgeItem',
    'AnchorItem',
    
    # 面板
    'NodeListPanel',
    'NodeConfigDialog',
    'ColorSettingsDialog',
    'NodeGroupManager',
    
    # 创建器
    'NodeCreatorManager'
]

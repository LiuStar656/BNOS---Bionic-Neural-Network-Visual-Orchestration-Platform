"""
功能定义模块 — 统一的 Action 数据结构
"""
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum


class ActionCategory(Enum):
    """功能分类枚举"""
    NODE = "node"           # 节点操作
    CANVAS = "canvas"       # 画布操作
    PROJECT = "project"     # 项目操作
    VIEW = "view"           # 视图操作
    SETTINGS = "settings"   # 设置操作
    TOOLS = "tools"         # 工具操作


@dataclass
class ActionContext:
    """执行上下文 - 传递给Action的参数"""
    node_name: Optional[str] = None
    node_list: Optional[list[str]] = None
    group_name: Optional[str] = None
    canvas_selection: Optional[Any] = None
    extra: dict = field(default_factory=dict)


@dataclass
class ActionDefinition:
    """功能定义 - 单一真实来源"""
    id: str                         # 唯一ID (如: "node.start")
    name_i18n: str                  # 显示名称 i18n key (如: "k_node_start")
    category: ActionCategory        # 分类
    description_i18n: Optional[str] = None  # 描述 i18n key
    shortcut_id: Optional[str] = None        # 快捷键ID
    requires_selection: bool = False         # 是否需要选中
    requires_node: bool = False              # 是否需要节点上下文
    requires_permission: Optional[str] = None  # 权限要求
    
    # 执行函数
    execute_fn: Optional[Callable[[ActionContext], bool]] = None
    
    # 状态检查函数
    is_enabled_fn: Optional[Callable[[ActionContext], bool]] = None
    is_checked_fn: Optional[Callable[[ActionContext], bool]] = None
    
    # 图标
    icon_id: Optional[str] = None

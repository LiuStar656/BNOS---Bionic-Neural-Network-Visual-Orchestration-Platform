"""
功能注册表模块 — 统一管理所有 Action 定义（单例模式）
"""
from typing import Dict, Optional, List
import sys
import os

_current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(_current_dir))))

try:
    from ui.core.actions.action_definition import ActionDefinition, ActionContext, ActionCategory
except ImportError:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'action_definition', 
        os.path.join(_current_dir, 'action_definition.py')
    )
    action_definition = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(action_definition)
    ActionDefinition = action_definition.ActionDefinition
    ActionContext = action_definition.ActionContext
    ActionCategory = action_definition.ActionCategory


class ActionRegistry:
    """统一功能注册表 - 单例模式"""
    
    _instance: Optional['ActionRegistry'] = None
    _actions: Dict[str, ActionDefinition] = {} # type: ignore
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register(cls, action_def: ActionDefinition): # type: ignore
        """注册功能定义"""
        cls._actions[action_def.id] = action_def
    
    @classmethod
    def get(cls, action_id: str) -> Optional[ActionDefinition]: # type: ignore
        """获取功能定义"""
        return cls._actions.get(action_id)
    
    @classmethod
    def all(cls, category: Optional[ActionCategory] = None) -> List[ActionDefinition]: # type: ignore
        """获取所有功能定义，可按分类过滤"""
        if category is None:
            return list(cls._actions.values())
        return [a for a in cls._actions.values() if a.category == category]
    
    @classmethod
    def execute(cls, action_id: str, context: Optional[ActionContext] = None) -> bool: # pyright: ignore[reportInvalidTypeForm]
        """执行功能"""
        action = cls.get(action_id)
        if not action or not action.execute_fn:
            return False
        
        if context is None:
            context = ActionContext()
        
        if action.requires_permission:
            if not cls._check_permission(action.requires_permission, context):
                return False
        
        return action.execute_fn(context)
    
    @classmethod
    def is_enabled(cls, action_id: str, context: Optional[ActionContext] = None) -> bool: # type: ignore
        """检查功能是否可用"""
        action = cls.get(action_id)
        if not action:
            return False
        if context is None:
            context = ActionContext()
        if action.is_enabled_fn:
            return action.is_enabled_fn(context)
        return True
    
    @classmethod
    def _check_permission(cls, permission: str, context: ActionContext) -> bool: # type: ignore
        """检查权限（预留接口）"""
        return True
    
    @classmethod
    def clear(cls):
        """清空注册表（用于测试）"""
        cls._actions = {}
    
    @classmethod
    def get_action_ids(cls) -> List[str]:
        """获取所有注册的功能ID"""
        return list(cls._actions.keys())

"""
依赖注入容器 — 解耦全局配置与具体实现
设计原则：面向接口编程，运行时可替换实现
"""
from abc import ABC, abstractmethod
from typing import TypeVar, Type, Dict, Any, Callable, Optional
from pathlib import Path
from ui.core.logger import logger
import json

T = TypeVar('T')


# ======================== 配置接口抽象 ========================

class IConfig(ABC):
    """配置接口 — 不依赖任何具体存储方式"""
    @abstractmethod
    def get(self, key: str, default=None): ...
    @abstractmethod
    def set(self, key: str, value): ...
    @abstractmethod
    def save(self): ...


class JsonFileConfig(IConfig):
    """JSON 文件配置实现（向后兼容 AppConfig）"""
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self):
        try:
            if self.config_path.exists():
                self._data = json.loads(self.config_path.read_text(encoding='utf-8'))
        except Exception as e:
            logger.warning("[DI] 配置加载失败: %s", e)
            self._data = {}

    def save(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        except Exception as e:
            logger.warning("[DI] 配置保存失败: %s", e)

    def get(self, key: str, default=None):
        keys = key.split('.')
        value = self._data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value):
        keys = key.split('.')
        data = self._data
        for k in keys[:-1]:
            data = data.setdefault(k, {})
        data[keys[-1]] = value


# ======================== DI 容器 ========================

class DIContainer:
    """轻量级 DI 容器 — 注册接口实现并解析依赖"""

    def __init__(self):
        self._factories: Dict[Type, Callable] = {}
        self._instances: Dict[Type, Any] = {}

    def register_instance(self, interface: Type[T], instance: T):
        """注册已创建的实例"""
        self._instances[interface] = instance

    def register_factory(self, interface: Type[T], factory: Callable[[], T]):
        """注册工厂方法（延迟创建）"""
        self._factories[interface] = factory

    def resolve(self, interface: Type[T]) -> T:
        """解析依赖"""
        if interface in self._instances:
            return self._instances[interface]
        if interface in self._factories:
            instance = self._factories[interface]()
            self._instances[interface] = instance
            return instance
        raise KeyError(f"[DI] 未注册接口: {interface}")

    def is_registered(self, interface: Type[T]) -> bool:
        """检查接口是否已注册"""
        return interface in self._instances or interface in self._factories


# 全局容器
container = DIContainer()

"""
依赖注入容器 — 解耦全局配置与具体实现
设计原则：面向接口编程，运行时可替换实现
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from ui.core.logger import logger

T = TypeVar("T")


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
        self._data: dict[str, Any] = {}
        self.load()

    def load(self):
        try:
            if self.config_path.exists():
                self._data = json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("[DI] 配置加载失败: %s", e)
            self._data = {}

    def save(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("[DI] 配置保存失败: %s", e)

    def get(self, key: str, default=None):
        keys = key.split(".")
        value = self._data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value):
        keys = key.split(".")
        data = self._data
        for k in keys[:-1]:
            data = data.setdefault(k, {})
        data[keys[-1]] = value


# ======================== DI 容器 ========================

_Scope = str  # "singleton" | "transient"
_Key = object  # 内部复合键: (interface_type, qualifier_name)


def _make_key(interface: type | str, name: str | None = None) -> _Key:
    """生成内部 lookup 键。interface 可以是 Type 或 str（名称注册）。"""
    return (interface, name)


_FACTORY = Callable[[], Any]


class DIContainer:
    """依赖注入容器 — 支持接口类型注册、命名实例、作用域。

    向后兼容原有 API（register_instance / register_factory / resolve / is_registered），
    同时提供统一的 register() / resolve() 增强方法。

    使用方式::

        # --- 基础用法（向后兼容）---
        container.register_instance(IConfig, config)
        container.resolve(IConfig)

        # --- 按名称注册（多实现）---
        container.register(ILogger, FileLogger(), name="file")
        container.register(ILogger, ConsoleLogger(), name="console")
        container.resolve(ILogger, name="file")  # → FileLogger 实例
        container.resolve("file")  # 也可以用名称直接解析

        # --- 瞬态作用域（每次新建）---
        container.register(IService, ServiceImpl, scope="transient")
        a = container.resolve(IService)
        b = container.resolve(IService)  # a is not b

        # --- 查询 ---
        container.is_registered(IConfig)  # True
        container.is_registered("file")  # True
        container.list_registered()  # → [(IConfig, None, "singleton"), ...]
    """

    def __init__(self):
        # {_Key: {"instance": Any, "factory": Callable | None, "scope": _Scope}}
        self._registry: dict[_Key, dict] = {}

    # ── 内部辅助 ──────────────────────────────────────────────

    def _entry(self, key: _Key) -> dict | None:
        return self._registry.get(key)

    def _resolve_entry(self, key: _Key) -> Any:
        entry = self._entry(key)
        if entry is None:
            raise KeyError(self._not_found_msg(key))
        if entry["factory"] is not None:
            if entry["scope"] == "transient":
                return entry["factory"]()
            # singleton: 仅在未实例化时调用工厂
            if entry["instance"] is None:
                entry["instance"] = entry["factory"]()
            return entry["instance"]
        return entry["instance"]

    def _not_found_msg(self, key: _Key) -> str:
        interface, name = key
        suffix = f" (name={name!r})" if name else ""
        available = self.list_registered()
        lines = []
        for iface, n, scope in available:
            label = f"{iface}"
            if n:
                label += f" [name={n!r}]"
            label += f" scope={scope}"
            lines.append(f"  - {label}")
        avail = "\n".join(lines) if lines else "  (none)"
        return f"[DI] 未注册: {interface}{suffix}\n已注册的服务:\n{avail}"

    # ── 旧 API（向后兼容）─────────────────────────────────────

    def register_instance(self, interface: type[T], instance: T):
        """注册已创建的实例（singleton）。"""
        key = _make_key(interface, None)
        self._registry[key] = {"instance": instance, "factory": None, "scope": "singleton"}

    def register_factory(self, interface: type[T], factory: Callable[[], T]):
        """注册工厂方法（singleton，延迟创建）。"""
        key = _make_key(interface, None)
        self._registry[key] = {"instance": None, "factory": factory, "scope": "singleton"}

    def resolve(self, interface: type[T] | str, name: str | None = None) -> T:
        """解析依赖。

        Args:
            interface: 接口类型 或 注册名称（str）。
            name: 可选名称，用于区分同一接口的多个实现。
        """
        if isinstance(interface, str):
            # 按名称查找：在所有注册中匹配 name
            for key, _entry in self._registry.items():
                iface, n = key
                if n == interface:
                    return self._resolve_entry(key)
            raise KeyError(self._not_found_msg(_make_key(interface, interface)))
        key = _make_key(interface, name)
        return self._resolve_entry(key)

    def is_registered(self, interface: type | str, name: str | None = None) -> bool:
        """检查接口或名称是否已注册。

        Args:
            interface: 接口类型 或 注册名称（str）。
            name: 可选名称限定。
        """
        if isinstance(interface, str):
            for key in self._registry:
                if key[1] == interface:
                    return True
            return False
        key = _make_key(interface, name)
        return key in self._registry

    # ── 新 API ─────────────────────────────────────────────────

    def register(
        self, interface: type | str, instance_or_factory: Any, *, name: str | None = None, scope: _Scope = "singleton"
    ):
        """统一注册方法。

        Args:
            interface: 接口类型（class/ABC）或字符串名称。
            instance_or_factory: 实例对象 或 无参工厂函数。
            name: 可选名称（多实现时用于区分）。
            scope: "singleton"（默认，单例缓存）或 "transient"（每次 resolve 新建）。
        """
        if scope not in ("singleton", "transient"):
            raise ValueError(f"scope 必须是 'singleton' 或 'transient'，实际: {scope!r}")
        key = _make_key(interface, name)
        if callable(instance_or_factory) and not isinstance(instance_or_factory, type):
            # 可调用非类 → 视为工厂函数
            self._registry[key] = {"instance": None, "factory": instance_or_factory, "scope": scope}
        else:
            # 实例对象
            self._registry[key] = {"instance": instance_or_factory, "factory": None, "scope": scope}

    def resolve_named(self, name: str) -> Any:
        """按名称解析（便捷方法）。"""
        return self.resolve(name)

    def list_registered(self) -> list[tuple]:
        """列出所有已注册的服务。

        Returns:
            list of (interface, name, scope)
        """
        return [(key[0], key[1], entry["scope"]) for key, entry in self._registry.items()]


# 全局容器
container = DIContainer()

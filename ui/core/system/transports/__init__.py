"""
ui/core/system/transports/ — 复合节点分布式传输适配层。

当前仅定义抽象接口，供未来多机编排扩展（SSH、gRPC 等）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class TransportHandler(ABC):
    """复合节点远程执行传输适配器。"""

    @abstractmethod
    def execute(self, comp_id: str, comp_def: dict) -> bool:
        """在远程环境执行复合节点，返回是否成功。"""
        ...


# 注册表
_HANDLERS: dict[str, type[TransportHandler]] = {}


def register_transport(name: str, handler_cls: type[TransportHandler]) -> None:
    _HANDLERS[name] = handler_cls


def get_transport_handler(name: str) -> TransportHandler:
    cls = _HANDLERS.get(name)
    if cls is None:
        from ui.core.i18n import t

        raise ValueError(t("k_transport_unknown").format(name=name))
    return cls()

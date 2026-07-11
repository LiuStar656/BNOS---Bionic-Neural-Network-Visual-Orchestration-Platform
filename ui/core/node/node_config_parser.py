"""
节点配置解析器 — 从 config.json 中提取参数定义和输入端口定义
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any


@dataclass
class ParameterDef:
    """单个参数的定义"""

    name: str
    type: str  # string|text|password|int|float|bool|enum|file|directory|color|range
    label: str
    default: Any = None
    required: bool = False
    description: str = ""
    # 数值约束
    min: float | None = None
    max: float | None = None
    step: float | None = None
    decimals: int = 2
    # 枚举约束
    options: list[str] = field(default_factory=list)
    # 文件约束
    file_filter: str = ""
    # 文本约束
    rows: int = 1
    # 动态选项（v1.1）
    dynamic_options: dict | None = None


@dataclass
class InputPortDef:
    """单个输入端口的定义

    source 字段控制端口的"数据来源模式"（与 AnchorManager.PortSource 对应）：
        - "node" : 需要从上游节点连入数据 → 在画布上生成锚点
        - "edit" : 用户手动输入（文本框 / 下拉框）→ 由参数面板渲染
        - "param": 可选参数（有 default）→ 由参数面板渲染
        - None   : 未指定 → 默认不生成锚点（保持旧节点兼容）
    """

    name: str  # 端口唯一标识
    label: str = ""  # 端口显示名称
    type: str = "default"  # 数据类型（用于连线兼容性校验）
    required: bool = False  # 是否必需连接
    description: str = ""  # 端口描述
    source: str | None = None  # 数据来源（见上方注释）


@dataclass
class OutputPortDef:
    """单个输出端口的定义

    节点可以有多个输出端口，每个输出端口都在画布右侧生成一个锚点，
    可供下游节点连线使用。
    """

    name: str  # 端口唯一标识
    label: str = ""  # 端口显示名称
    type: str = "default"  # 数据类型
    description: str = ""  # 端口描述


class NodeConfigParser:
    """节点配置解析器"""

    @staticmethod
    def parse(config: dict) -> list[ParameterDef]:
        """从 config.json 字典中提取参数定义列表"""
        raw = config.get("parameters", [])
        if not raw or not isinstance(raw, list):
            return []
        known_fields = {f.name for f in fields(ParameterDef)}
        result = []
        for p in raw:
            if not isinstance(p, dict):
                continue
            result.append(ParameterDef(**{k: v for k, v in p.items() if k in known_fields}))
        return result

    @staticmethod
    def extract_values(config: dict) -> dict[str, Any]:
        """从 config.json 中提取参数实际值（参数名 → 当前值）"""
        result = {}
        params = config.get("parameters")
        if not isinstance(params, list):
            return result
        for p_def in params:
            if not isinstance(p_def, dict):
                continue
            name = p_def.get("name")
            if not name:
                continue
            result[name] = config.get(name, p_def.get("default"))
        return result

    @staticmethod
    def has_parameters(config: dict) -> bool:
        """检查配置是否包含参数定义"""
        return bool(config.get("parameters"))

    @staticmethod
    def parse_input_ports(config: dict) -> list[InputPortDef]:
        """从 config.json 中提取输入端口定义列表"""
        raw = config.get("input_ports", [])
        if not raw or not isinstance(raw, list):
            return []
        known_fields = {f.name for f in fields(InputPortDef)}
        result = []
        for p in raw:
            if not isinstance(p, dict):
                continue
            result.append(InputPortDef(**{k: v for k, v in p.items() if k in known_fields}))
        return result

    @staticmethod
    def has_input_ports(config: dict) -> bool:
        """检查配置是否包含输入端口定义"""
        return bool(config.get("input_ports"))

    @staticmethod
    def get_input_port_names(config: dict) -> list[str]:
        """获取所有输入端口名称"""
        ports = config.get("input_ports")
        if not isinstance(ports, list):
            return []
        return [p.get("name", "") for p in ports if isinstance(p, dict) and p.get("name")]

    # -- 输出端口 --
    @staticmethod
    def parse_output_ports(config: dict) -> list[OutputPortDef]:
        """从 config.json 中提取输出端口定义列表"""
        raw = config.get("output_ports", [])
        if not raw or not isinstance(raw, list):
            return []
        known_fields = {f.name for f in fields(OutputPortDef)}
        result = []
        for p in raw:
            if not isinstance(p, dict):
                continue
            result.append(OutputPortDef(**{k: v for k, v in p.items() if k in known_fields}))
        return result

    @staticmethod
    def has_output_ports(config: dict) -> bool:
        """检查配置是否包含输出端口定义"""
        return bool(config.get("output_ports"))

    @staticmethod
    def get_output_port_names(config: dict) -> list[str]:
        """获取所有输出端口名称"""
        ports = config.get("output_ports")
        if not isinstance(ports, list):
            return []
        return [p.get("name", "") for p in ports if isinstance(p, dict) and p.get("name")]

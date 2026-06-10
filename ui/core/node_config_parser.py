"""
节点配置解析器 — 从 config.json 中提取参数定义和输入端口定义
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ParameterDef:
    """单个参数的定义"""
    name: str
    type: str          # string|text|password|int|float|bool|enum|file|directory|color|range
    label: str
    default: Any = None
    required: bool = False
    # 数值约束
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    decimals: int = 2
    # 枚举约束
    options: list[str] = field(default_factory=list)
    # 文件约束
    file_filter: str = ""
    # 文本约束
    rows: int = 1
    # 动态选项（v1.1）
    dynamic_options: Optional[dict] = None


@dataclass
class InputPortDef:
    """单个输入端口的定义"""
    name: str           # 端口唯一标识
    label: str = ""     # 端口显示名称
    type: str = "default"  # 数据类型（用于连线兼容性校验）
    required: bool = False  # 是否必需连接
    description: str = ""   # 端口描述


class NodeConfigParser:
    """节点配置解析器"""

    @staticmethod
    def parse(config: dict) -> list[ParameterDef]:
        """从 config.json 字典中提取参数定义列表"""
        raw = config.get("parameters", [])
        if not raw:
            return []
        return [ParameterDef(**p) for p in raw]

    @staticmethod
    def extract_values(config: dict) -> dict[str, Any]:
        """从 config.json 中提取参数实际值（参数名 → 当前值）"""
        result = {}
        for p_def in (config.get("parameters") or []):
            name = p_def["name"]
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
        if not raw:
            return []
        return [InputPortDef(**p) for p in raw]

    @staticmethod
    def has_input_ports(config: dict) -> bool:
        """检查配置是否包含输入端口定义"""
        return bool(config.get("input_ports"))

    @staticmethod
    def get_input_port_names(config: dict) -> list[str]:
        """获取所有输入端口名称"""
        return [p["name"] for p in (config.get("input_ports") or [])]

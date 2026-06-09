"""
节点配置解析器 — 从 config.json 中提取参数定义
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

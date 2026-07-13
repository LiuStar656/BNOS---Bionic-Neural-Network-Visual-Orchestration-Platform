"""
配置文件合并工具 — 已统一为 node_config.json 单文件格式

提供配置迁移和验证功能，保留备份恢复能力处理历史迁移数据。
"""

from __future__ import annotations

import json
import os
import shutil

from ui.core.logger import logger


class ConfigMerger:
    """配置文件合并工具（迁移后仅保留备份恢复能力）"""

    def __init__(self):
        self.backup_dir = ".config_backup"

    def merge_configs(self, node_path: str) -> dict:
        """读取 node_config.json（统一配置，无需合并）

        Args:
            node_path: 节点目录路径

        Returns:
            配置字典
        """
        config_path = os.path.join(node_path, "node_config.json")

        config = self._load_config_json(config_path)
        if not config:
            raise ValueError("无法加载 node_config.json")

        logger.info("配置加载完成: %s", node_path)
        return config

    def _load_config_json(self, config_path: str) -> dict:
        """加载 node_config.json"""
        if not os.path.exists(config_path):
            return {}

        try:
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        except (ValueError, OSError) as e:
            logger.warning("加载 node_config.json 失败: %s", e)
            return {}

    def _save_unified_config(self, unified_path: str, config: dict):
        """保存统一配置文件"""
        try:
            with open(unified_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except (ValueError, OSError) as e:
            raise ValueError(f"保存 node_config.json 失败: {e}") from e

    def _backup_legacy_configs(self, node_path: str):
        """备份旧配置文件"""
        backup_path = os.path.join(node_path, self.backup_dir)
        os.makedirs(backup_path, exist_ok=True)

        # 备份 config.json 和 start.json
        for filename in ["config.json", "start.json"]:
            src = os.path.join(node_path, filename)
            if os.path.exists(src):
                dst = os.path.join(backup_path, filename)
                shutil.copy2(src, dst)
                logger.debug("已备份 %s", filename)

    def restore_legacy_configs(self, node_path: str):
        """恢复旧配置文件"""
        backup_path = os.path.join(node_path, self.backup_dir)
        if not os.path.exists(backup_path):
            return

        # 恢复 config.json 和 start.json
        for filename in ["config.json", "start.json"]:
            src = os.path.join(backup_path, filename)
            dst = os.path.join(node_path, filename)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                logger.debug("已恢复 %s", filename)

        # 删除备份目录
        try:
            shutil.rmtree(backup_path)
            logger.debug("已删除备份目录")
        except OSError as e:
            logger.warning("删除备份目录失败: %s", e)

    def validate_unified_config(self, config: dict) -> list:
        """验证统一配置的完整性

        Args:
            config: 配置字典

        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors = []

        # 必需字段检查
        required_fields = ["node_name", "entry"]
        for field in required_fields:
            if field not in config:
                errors.append(f"缺少必需字段: {field}")

        # 节点名称验证
        node_name = config.get("node_name", "")
        if not node_name:
            errors.append("node_name 不能为空")
        elif not self._is_valid_node_name(node_name):
            errors.append("node_name 只能包含字母、数字、下划线和连字符")

        # 参数验证
        if "parameters" in config:
            param_errors = self._validate_parameters(config["parameters"])
            errors.extend(param_errors)

        # 端口验证
        if "input_ports" in config:
            port_errors = self._validate_ports(config["input_ports"], "input")
            errors.extend(port_errors)

        if "output_ports" in config:
            port_errors = self._validate_ports(config["output_ports"], "output")
            errors.extend(port_errors)

        return errors

    def _is_valid_node_name(self, name: str) -> bool:
        """验证节点名称格式"""
        import re

        return bool(re.match(r"^[a-zA-Z0-9_-]+$", name))

    def _validate_parameters(self, parameters: list) -> list:
        """验证参数定义"""
        errors = []

        if not isinstance(parameters, list):
            errors.append("parameters 必须是数组")
            return errors

        for i, param in enumerate(parameters):
            if not isinstance(param, dict):
                errors.append(f"parameters[{i}] 必须是对象")
                continue

            # 检查必需字段
            if "name" not in param:
                errors.append(f"parameters[{i}] 缺少 name 字段")
            if "type" not in param:
                errors.append(f"parameters[{i}] 缺少 type 字段")

            # 类型验证
            valid_types = [
                "string",
                "text",
                "password",
                "int",
                "float",
                "bool",
                "enum",
                "file",
                "directory",
                "color",
                "range",
            ]
            param_type = param.get("type")
            if param_type not in valid_types:
                errors.append(f"parameters[{i}].type 无效: {param_type}")

            # 枚举值验证
            if param_type == "enum" and "options" not in param:
                errors.append(f"parameters[{i}] (enum) 必须提供 options")

        return errors

    def _validate_ports(self, ports: list, port_type: str) -> list:
        """验证端口定义"""
        errors = []

        if not isinstance(ports, list):
            errors.append(f"{port_type}_ports 必须是数组")
            return errors

        for i, port in enumerate(ports):
            if not isinstance(port, dict):
                errors.append(f"{port_type}_ports[{i}] 必须是对象")
                continue

            # 检查必需字段
            if "name" not in port:
                errors.append(f"{port_type}_ports[{i}] 缺少 name 字段")
            if "type" not in port:
                errors.append(f"{port_type}_ports[{i}] 缺少 type 字段")

        return errors


class ConfigDetector:
    """配置文件检测器"""

    @staticmethod
    def detect_config_type(node_path: str) -> str:
        """检测节点使用的配置类型

        Args:
            node_path: 节点目录路径

        Returns:
            配置类型: "unified" | "none"
        """
        unified_exists = os.path.exists(os.path.join(node_path, "node_config.json"))

        if unified_exists:
            return "unified"
        return "none"

    @staticmethod
    def get_config_files(node_path: str) -> list:
        """获取节点目录中的配置文件列表"""
        files = []

        for filename in ["node_config.json", "start.json"]:
            filepath = os.path.join(node_path, filename)
            if os.path.exists(filepath):
                files.append(filename)

        return files

    @staticmethod
    def has_backup(node_path: str) -> bool:
        """检查是否有配置备份"""
        backup_path = os.path.join(node_path, ".config_backup")
        return os.path.exists(backup_path)


# ============================================================
# 全局工具函数 — 统一配置读写
# ============================================================


def get_config_path(node_path: str) -> str:
    """获取节点的主配置文件路径（始终返回 node_config.json）

    所有读写节点配置的代码应通过此函数获取路径，
    而非硬编码文件名。
    """
    return os.path.join(node_path, "node_config.json")


def load_node_config(node_path: str) -> dict:
    """加载节点主配置文件（node_config.json）"""
    config_path = get_config_path(node_path)
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_node_config_file(node_path: str, config: dict):
    """保存节点配置到 node_config.json"""
    config_path = get_config_path(node_path)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

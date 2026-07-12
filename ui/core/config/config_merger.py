"""
配置文件合并工具 — 将 config.json 和 start.json 合并为 node_config.json

支持向后兼容，提供配置迁移和验证功能。
"""

from __future__ import annotations

import json
import os
import shutil

from ui.core.logger import logger


class ConfigMerger:
    """配置文件合并工具"""

    def __init__(self):
        self.backup_dir = ".config_backup"

    def merge_configs(self, node_path: str) -> dict:
        """合并 config.json 和 start.json 为 node_config.json

        Args:
            node_path: 节点目录路径

        Returns:
            合并后的配置字典
        """
        config_path = os.path.join(node_path, "config.json")
        start_path = os.path.join(node_path, "start.json")
        unified_path = os.path.join(node_path, "node_config.json")

        # 加载基础配置
        config = self._load_config_json(config_path)
        if not config:
            raise ValueError("无法加载 config.json")

        # 合并启动配置
        start_config = self._load_start_json(start_path)
        merged = self._merge_configs(config, start_config)

        # 保存统一配置
        self._save_unified_config(unified_path, merged)

        # 备份旧配置
        self._backup_legacy_configs(node_path)

        logger.info("配置合并完成: %s", node_path)
        return merged

    def _load_config_json(self, config_path: str) -> dict:
        """加载 config.json"""
        if not os.path.exists(config_path):
            return {}

        try:
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        except (ValueError, OSError) as e:
            logger.warning("加载 config.json 失败: %s", e)
            return {}

    def _load_start_json(self, start_path: str) -> dict:
        """加载 start.json"""
        if not os.path.exists(start_path):
            return {}

        try:
            with open(start_path, encoding="utf-8") as f:
                return json.load(f)
        except (ValueError, OSError) as e:
            logger.warning("加载 start.json 失败: %s", e)
            return {}

    def _merge_configs(self, config: dict, start_config: dict) -> dict:
        """合并两个配置文件

        Args:
            config: config.json 内容
            start_config: start.json 内容

        Returns:
            合并后的配置
        """
        merged = config.copy()

        # 处理 start.json 的多节点格式
        if "nodes" in start_config and isinstance(start_config["nodes"], list):
            for node in start_config["nodes"]:
                if node.get("name") == config.get("node_name"):
                    # 合并启动配置
                    merged.update({"entry": node.get("entry", "listener.py"), "python_exe": node.get("python_exe", "")})

                    # 合并运行时配置
                    if "config" in node:
                        merged.update(node["config"])
                    break

        # 处理单节点格式
        elif start_config.get("name") == config.get("node_name"):
            merged.update(
                {"entry": start_config.get("entry", "listener.py"), "python_exe": start_config.get("python_exe", "")}
            )
            if "config" in start_config:
                merged.update(start_config["config"])

        return merged

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
            配置类型: "unified" | "legacy" | "config_only" | "none"
        """
        config_exists = os.path.exists(os.path.join(node_path, "config.json"))
        start_exists = os.path.exists(os.path.join(node_path, "start.json"))
        unified_exists = os.path.exists(os.path.join(node_path, "node_config.json"))

        if unified_exists:
            return "unified"
        elif config_exists and start_exists:
            return "legacy"
        elif config_exists:
            return "config_only"
        else:
            return "none"

    @staticmethod
    def get_config_files(node_path: str) -> list:
        """获取节点目录中的配置文件列表"""
        files = []

        for filename in ["config.json", "start.json", "node_config.json"]:
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
    """获取节点的主配置文件路径（优先 node_config.json，回退 config.json）

    所有读写节点配置的代码应通过此函数获取路径，
    而非硬编码 "config.json"。
    """
    node_config = os.path.join(node_path, "node_config.json")
    if os.path.exists(node_config):
        return node_config
    return os.path.join(node_path, "config.json")


def load_node_config(node_path: str) -> dict:
    """加载节点主配置文件（优先 node_config.json，回退 config.json）"""
    config_path = get_config_path(node_path)
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_node_config_file(node_path: str, config: dict):
    """保存节点配置到主配置文件（node_config.json 或 config.json）"""
    config_path = get_config_path(node_path)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

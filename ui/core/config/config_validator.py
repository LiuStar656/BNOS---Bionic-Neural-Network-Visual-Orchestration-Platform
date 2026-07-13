"""
配置验证工具 — 验证 node_config.json 的完整性和正确性
"""

from __future__ import annotations

import json
import os
import re


class ConfigValidator:
    """配置验证工具"""

    VALID_PARAM_TYPES = [
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

    REQUIRED_FIELDS = ["node_name", "entry"]

    @staticmethod
    def validate_unified_config(config: dict) -> list:
        """验证统一配置的完整性

        Args:
            config: 配置字典

        Returns:
            错误信息列表，空列表表示验证通过
        """
        errors = []

        # 必需字段检查
        for field in ConfigValidator.REQUIRED_FIELDS:
            if field not in config:
                errors.append(f"缺少必需字段: {field}")

        # 节点名称验证
        node_name = config.get("node_name", "")
        if node_name:
            if not ConfigValidator._is_valid_node_name(node_name):
                errors.append(f"node_name 格式无效: {node_name}")
        else:
            errors.append("node_name 不能为空")

        # 入口文件验证
        entry = config.get("entry", "")
        if entry and not ConfigValidator._is_valid_entry(entry):
            errors.append(f"entry 格式无效: {entry}")

        # 参数验证
        if "parameters" in config:
            param_errors = ConfigValidator._validate_parameters(config["parameters"])
            errors.extend(param_errors)

        # 端口验证
        if "input_ports" in config:
            port_errors = ConfigValidator._validate_ports(config["input_ports"], "input")
            errors.extend(port_errors)

        if "output_ports" in config:
            port_errors = ConfigValidator._validate_ports(config["output_ports"], "output")
            errors.extend(port_errors)

        # 资源限制验证
        if "resource_limit" in config:
            resource_errors = ConfigValidator._validate_resource_limit(config["resource_limit"])
            errors.extend(resource_errors)

        return errors

    @staticmethod
    def validate_config_file(file_path: str) -> tuple[bool, list]:
        """验证配置文件

        Args:
            file_path: 配置文件路径

        Returns:
            (是否有效, 错误列表)
        """
        if not os.path.exists(file_path):
            return False, ["文件不存在"]

        try:
            with open(file_path, encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            return False, [f"JSON 解析失败: {e}"]
        except (ValueError, OSError) as e:
            return False, [f"文件读取失败: {e}"]

        errors = ConfigValidator.validate_unified_config(config)
        return len(errors) == 0, errors

    @staticmethod
    def validate_project_configs(project_path: str) -> dict:
        """验证项目中所有节点的配置

        Args:
            project_path: 项目路径

        Returns:
            {node_name: (is_valid, errors)}
        """
        results = {}
        nodes_dir = os.path.join(project_path, "nodes")

        if not os.path.exists(nodes_dir):
            return results

        for node_name in os.listdir(nodes_dir):
            node_path = os.path.join(nodes_dir, node_name)
            if not os.path.isdir(node_path):
                continue

            # 检查统一配置
            unified_path = os.path.join(node_path, "node_config.json")
            if os.path.exists(unified_path):
                is_valid, errors = ConfigValidator.validate_config_file(unified_path)
                results[node_name] = (is_valid, errors)

            # 检查旧格式配置
            config_path = os.path.join(node_path, "node_config.json")
            if os.path.exists(config_path):
                is_valid, errors = ConfigValidator.validate_config_file(config_path)
                if node_name not in results:
                    results[node_name] = (is_valid, errors)

        return results

    @staticmethod
    def _is_valid_node_name(name: str) -> bool:
        """验证节点名称格式"""
        if not name:
            return False
        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            return False
        if len(name) > 64:
            return False
        return True

    @staticmethod
    def _is_valid_entry(entry: str) -> bool:
        """验证入口文件格式"""
        if not entry:
            return False
        if not re.match(r"^[a-zA-Z0-9_\-./]+\.(py|rs|js|ts|go)$", entry):
            return False
        return True

    @staticmethod
    def _validate_parameters(parameters: list) -> list:
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
            param_type = param.get("type")
            if param_type and param_type not in ConfigValidator.VALID_PARAM_TYPES:
                errors.append(f"parameters[{i}].type 无效: {param_type}")

            # 枚举值验证
            if param_type == "enum" and "options" not in param:
                errors.append(f"parameters[{i}] (enum) 必须提供 options")

        return errors

    @staticmethod
    def _validate_ports(ports: list, port_type: str) -> list:
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

    @staticmethod
    def _validate_resource_limit(resource_limit: dict) -> list:
        """验证资源限制"""
        errors = []

        if not isinstance(resource_limit, dict):
            errors.append("resource_limit 必须是对象")
            return errors

        # 内存限制验证
        memory_mb = resource_limit.get("memory_mb", 0)
        if not isinstance(memory_mb, int | float):
            errors.append("resource_limit.memory_mb 必须是数字")
        elif memory_mb < 256:
            errors.append("resource_limit.memory_mb 至少为 256MB")
        elif memory_mb > 65536:
            errors.append("resource_limit.memory_mb 最大为 65536MB")

        # CPU 限制验证
        cpu_percent = resource_limit.get("cpu_percent", 0)
        if not isinstance(cpu_percent, int | float):
            errors.append("resource_limit.cpu_percent 必须是数字")
        elif cpu_percent < 10:
            errors.append("resource_limit.cpu_percent 至少为 10%")
        elif cpu_percent > 800:
            errors.append("resource_limit.cpu_percent 最大为 800%")

        return errors

    @staticmethod
    def format_errors(errors: list) -> str:
        """格式化错误信息为可读字符串"""
        if not errors:
            return "配置验证通过"

        formatted = ["配置验证失败:"]
        for i, error in enumerate(errors, 1):
            formatted.append(f"  {i}. {error}")

        return "\n".join(formatted)

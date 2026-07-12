"""
配置迁移向导 — 批量迁移项目中的配置文件到统一格式
"""

from __future__ import annotations

import os

from ui.core.config.config_merger import ConfigDetector, ConfigMerger
from ui.core.config.config_validator import ConfigValidator
from ui.core.logger import logger


class MigrationWizard:
    """配置迁移向导 — 批量迁移节点配置到统一格式"""

    def __init__(self):
        self.merger = ConfigMerger()
        self.results = {
            "total": 0,
            "migrated": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
        }

    def migrate_project(self, project_path: str) -> dict:
        """迁移整个项目的配置到统一格式

        Args:
            project_path: 项目路径

        Returns:
            迁移结果统计
        """
        self.results = {
            "total": 0,
            "migrated": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [],
        }

        nodes_dir = os.path.join(project_path, "nodes")
        if not os.path.exists(nodes_dir):
            logger.warning("nodes 目录不存在: %s", nodes_dir)
            return self.results

        for node_name in os.listdir(nodes_dir):
            node_path = os.path.join(nodes_dir, node_name)
            if not os.path.isdir(node_path):
                continue

            self.results["total"] += 1
            self._migrate_node(node_path, node_name)

        logger.info(
            "迁移完成: 总数=%d, 已迁移=%d, 已跳过=%d, 失败=%d",
            self.results["total"],
            self.results["migrated"],
            self.results["skipped"],
            self.results["failed"],
        )

        return self.results

    def _migrate_node(self, node_path: str, node_name: str):
        """迁移单个节点的配置"""
        config_type = ConfigDetector.detect_config_type(node_path)

        if config_type == "unified":
            # 已使用统一配置，跳过
            self.results["skipped"] += 1
            logger.debug("节点 %s 已使用统一配置，跳过", node_name)
            return

        if config_type == "none":
            # 无配置文件，跳过
            self.results["skipped"] += 1
            logger.debug("节点 %s 无配置文件，跳过", node_name)
            return

        try:
            # 合并配置
            self.merger.merge_configs(node_path)

            # 验证合并结果
            unified_path = os.path.join(node_path, "node_config.json")
            is_valid, errors = ConfigValidator.validate_config_file(unified_path)

            if is_valid:
                self.results["migrated"] += 1
                logger.info("节点 %s 迁移成功", node_name)
            else:
                self.results["failed"] += 1
                error_msg = f"节点 {node_name} 配置验证失败: {', '.join(errors)}"
                self.results["errors"].append(error_msg)
                logger.error(error_msg)
        except Exception as e:
            self.results["failed"] += 1
            error_msg = f"节点 {node_name} 迁移失败: {e}"
            self.results["errors"].append(error_msg)
            logger.error(error_msg)

    def migrate_node(self, node_path: str) -> bool:
        """迁移单个节点配置

        Args:
            node_path: 节点目录路径

        Returns:
            是否迁移成功
        """
        # 检查是否已使用统一配置
        config_type = ConfigDetector.detect_config_type(node_path)

        if config_type == "unified":
            logger.debug("节点 %s 已使用统一配置，跳过", os.path.basename(node_path))
            self.results["skipped"] += 1
            return False

        if config_type == "none":
            logger.warning("节点 %s 无配置文件", os.path.basename(node_path))
            self.results["skipped"] += 1
            return False

        try:
            merged = self.merger.merge_configs(node_path)

            # 验证
            errors = ConfigValidator.validate_unified_config(merged)
            if errors:
                self.results["failed"] += 1
                self.results["errors"].append(
                    f"节点 {os.path.basename(node_path)} 配置验证失败: {ConfigValidator.format_errors(errors)}"
                )
                logger.error("配置验证失败: %s", ConfigValidator.format_errors(errors))
                return False

            self.results["migrated"] += 1
            logger.info("节点 %s 迁移成功", os.path.basename(node_path))
            return True
        except Exception as e:
            self.results["failed"] += 1
            self.results["errors"].append(f"节点 {os.path.basename(node_path)} 迁移失败: {e}")
            logger.error("节点迁移失败: %s", e)
            return False

    def rollback_node(self, node_path: str) -> bool:
        """回滚节点的配置迁移

        Args:
            node_path: 节点目录路径

        Returns:
            是否回滚成功
        """
        try:
            # 检查是否有备份
            if not ConfigDetector.has_backup(node_path):
                logger.warning("节点 %s 无备份，无法回滚", os.path.basename(node_path))
                return False

            # 恢复旧配置
            self.merger.restore_legacy_configs(node_path)

            # 删除统一配置文件
            unified_path = os.path.join(node_path, "node_config.json")
            if os.path.exists(unified_path):
                os.remove(unified_path)

            logger.info("节点 %s 回滚成功", os.path.basename(node_path))
            return True
        except Exception as e:
            logger.error("回滚失败: %s", e)
            return False

    def rollback_project(self, project_path: str) -> dict:
        """回滚整个项目的配置迁移

        Args:
            project_path: 项目路径

        Returns:
            回滚结果统计
        """
        results = {
            "total": 0,
            "rolled_back": 0,
            "failed": 0,
        }

        nodes_dir = os.path.join(project_path, "nodes")
        if not os.path.exists(nodes_dir):
            return results

        for node_name in os.listdir(nodes_dir):
            node_path = os.path.join(nodes_dir, node_name)
            if not os.path.isdir(node_path):
                continue

            results["total"] += 1

            if self.rollback_node(node_path):
                results["rolled_back"] += 1
            else:
                results["failed"] += 1

        logger.info(
            "回滚完成: 总数=%d, 已回滚=%d, 失败=%d",
            results["total"],
            results["rolled_back"],
            results["failed"],
        )

        return results

    def get_migration_report(self) -> str:
        """获取迁移报告"""
        if self.results["total"] == 0:
            return "未执行迁移"

        report = [
            "=== 配置迁移报告 ===",
            f"总数: {self.results['total']}",
            f"已迁移: {self.results['migrated']}",
            f"已跳过: {self.results['skipped']}",
            f"失败: {self.results['failed']}",
        ]

        if self.results["errors"]:
            report.append("")
            report.append("=== 错误详情 ===")
            for error in self.results["errors"]:
                report.append(f"  - {error}")

        return "\n".join(report)

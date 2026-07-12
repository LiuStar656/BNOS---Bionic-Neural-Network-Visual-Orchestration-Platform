"""
配置验证和迁移向导测试
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest

from ui.core.config.config_merger import ConfigMerger
from ui.core.config.config_validator import ConfigValidator
from ui.core.config.migration_wizard import MigrationWizard


class TestConfigValidator(unittest.TestCase):
    """配置验证测试"""

    def test_valid_config(self):
        """测试有效配置"""
        config = {
            "node_name": "test_node",
            "entry": "listener.py",
            "parameters": [
                {"name": "param1", "type": "string", "default": "value1"},
                {"name": "param2", "type": "int", "default": 42},
            ],
            "input_ports": [
                {"name": "input1", "type": "string"},
            ],
            "output_ports": [
                {"name": "output1", "type": "string"},
            ],
            "resource_limit": {
                "memory_mb": 1024,
                "cpu_percent": 100,
            },
        }

        errors = ConfigValidator.validate_unified_config(config)
        self.assertEqual(len(errors), 0)

    def test_missing_required_fields(self):
        """测试缺少必需字段"""
        config = {
            "node_name": "test_node",
            # 缺少 entry
        }

        errors = ConfigValidator.validate_unified_config(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("entry" in err for err in errors))

    def test_invalid_node_name(self):
        """测试无效的节点名称"""
        config = {
            "node_name": "test node with spaces",
            "entry": "listener.py",
        }

        errors = ConfigValidator.validate_unified_config(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("node_name" in err for err in errors))

    def test_invalid_param_type(self):
        """测试无效的参数类型"""
        config = {
            "node_name": "test_node",
            "entry": "listener.py",
            "parameters": [
                {"name": "param1", "type": "invalid_type"},
            ],
        }

        errors = ConfigValidator.validate_unified_config(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("invalid_type" in err for err in errors))

    def test_enum_without_options(self):
        """测试枚举类型缺少选项"""
        config = {
            "node_name": "test_node",
            "entry": "listener.py",
            "parameters": [
                {"name": "param1", "type": "enum"},
            ],
        }

        errors = ConfigValidator.validate_unified_config(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("enum" in err.lower() for err in errors))

    def test_invalid_resource_limit(self):
        """测试无效的资源限制"""
        config = {
            "node_name": "test_node",
            "entry": "listener.py",
            "resource_limit": {
                "memory_mb": 100,  # 低于最小值
                "cpu_percent": 5,  # 低于最小值
            },
        }

        errors = ConfigValidator.validate_unified_config(config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("memory" in err for err in errors))
        self.assertTrue(any("cpu" in err.lower() for err in errors))

    def test_validate_config_file(self):
        """测试验证配置文件"""
        temp_dir = tempfile.mkdtemp()
        config_path = os.path.join(temp_dir, "node_config.json")

        # 写入有效配置
        valid_config = {
            "node_name": "test_node",
            "entry": "listener.py",
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(valid_config, f)

        is_valid, errors = ConfigValidator.validate_config_file(config_path)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # 写入无效JSON
        with open(config_path, "w") as f:
            f.write("invalid json")

        is_valid, errors = ConfigValidator.validate_config_file(config_path)
        self.assertFalse(is_valid)
        self.assertTrue(any("JSON" in err for err in errors))

        shutil.rmtree(temp_dir)

    def test_format_errors(self):
        """测试格式化错误信息"""
        errors = ["缺少必需字段: entry", "node_name 不能为空"]
        formatted = ConfigValidator.format_errors(errors)

        self.assertIn("配置验证失败", formatted)
        self.assertIn("entry", formatted)
        self.assertIn("node_name", formatted)


class TestMigrationWizard(unittest.TestCase):
    """迁移向导测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.wizard = MigrationWizard()
        self.merger = ConfigMerger()

    def tearDown(self):
        """测试后清理"""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_migrate_single_node(self):
        """测试迁移单个节点"""
        # 创建旧格式配置
        config = {
            "node_name": "test_node",
            "parameters": [
                {"name": "param1", "type": "string", "default": "value1"},
            ],
        }

        start_config = {
            "nodes": [
                {
                    "name": "test_node",
                    "entry": "listener.py",
                    "config": {
                        "listen_upper_file": "../data/upper.json",
                    },
                },
            ],
        }

        with open(os.path.join(self.temp_dir, "config.json"), "w") as f:
            json.dump(config, f)
        with open(os.path.join(self.temp_dir, "start.json"), "w") as f:
            json.dump(start_config, f)

        # 执行迁移
        success = self.wizard.migrate_node(self.temp_dir)
        self.assertTrue(success)

        # 验证统一配置文件
        unified_path = os.path.join(self.temp_dir, "node_config.json")
        self.assertTrue(os.path.exists(unified_path))

        # 验证配置内容
        with open(unified_path, encoding="utf-8") as f:
            unified = json.load(f)

        self.assertEqual(unified["node_name"], "test_node")
        self.assertEqual(unified["entry"], "listener.py")
        self.assertEqual(unified["listen_upper_file"], "../data/upper.json")

    def test_rollback_node(self):
        """测试回滚节点"""
        # 创建旧格式配置
        config = {"node_name": "test_node"}
        start_config = {"nodes": [{"name": "test_node", "entry": "listener.py"}]}

        with open(os.path.join(self.temp_dir, "config.json"), "w") as f:
            json.dump(config, f)
        with open(os.path.join(self.temp_dir, "start.json"), "w") as f:
            json.dump(start_config, f)

        # 迁移
        self.wizard.migrate_node(self.temp_dir)

        # 验证有备份
        from ui.core.config.config_merger import ConfigDetector

        self.assertTrue(ConfigDetector.has_backup(self.temp_dir))

        # 回滚
        success = self.wizard.rollback_node(self.temp_dir)
        self.assertTrue(success)

        # 验证旧配置已恢复
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "config.json")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "start.json")))

        # 验证统一配置已删除
        self.assertFalse(os.path.exists(os.path.join(self.temp_dir, "node_config.json")))

    def test_migrate_project(self):
        """测试迁移整个项目"""
        project_path = self.temp_dir
        nodes_dir = os.path.join(project_path, "nodes")
        os.makedirs(nodes_dir, exist_ok=True)

        # 创建两个旧格式节点
        for i in range(2):
            node_dir = os.path.join(nodes_dir, f"node_{i}")
            os.makedirs(node_dir, exist_ok=True)

            config = {"node_name": f"node_{i}"}
            start_config = {
                "nodes": [
                    {
                        "name": f"node_{i}",
                        "entry": "listener.py",
                    }
                ],
            }

            with open(os.path.join(node_dir, "config.json"), "w") as f:
                json.dump(config, f)
            with open(os.path.join(node_dir, "start.json"), "w") as f:
                json.dump(start_config, f)

        # 执行项目迁移
        results = self.wizard.migrate_project(project_path)

        self.assertEqual(results["total"], 2)
        self.assertEqual(results["migrated"], 2)
        self.assertEqual(results["failed"], 0)

    def test_migration_report(self):
        """测试迁移报告"""
        self.wizard.results = {
            "total": 5,
            "migrated": 3,
            "skipped": 1,
            "failed": 1,
            "errors": ["节点 bad_node 配置验证失败"],
        }

        report = self.wizard.get_migration_report()

        self.assertIn("总数: 5", report)
        self.assertIn("已迁移: 3", report)
        self.assertIn("bad_node", report)

    def test_migrate_already_unified(self):
        """测试跳过已迁移的节点"""
        # 创建统一配置
        unified_config = {
            "node_name": "test_node",
            "entry": "listener.py",
        }
        with open(os.path.join(self.temp_dir, "node_config.json"), "w") as f:
            json.dump(unified_config, f)

        # 迁移（应该跳过）
        success = self.wizard.migrate_node(self.temp_dir)
        self.assertFalse(success)  # 已统一配置，跳过

        # 验证被标记为跳过
        self.assertEqual(self.wizard.results["skipped"], 1)


if __name__ == "__main__":
    import shutil

    unittest.main()

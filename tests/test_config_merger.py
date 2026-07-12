"""
配置合并工具测试 — 验证向后兼容性和新配置支持
"""

import json
import os
import tempfile
import unittest

from ui.core.config.config_merger import ConfigDetector, ConfigMerger


class TestConfigMerger(unittest.TestCase):
    """配置合并工具测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.merger = ConfigMerger()

    def tearDown(self):
        """测试后清理"""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_merge_unified_config(self):
        """测试统一配置加载"""
        # 创建 node_config.json
        unified_config = {
            "node_name": "test_node",
            "entry": "listener.py",
            "parameters": [{"name": "param1", "type": "string", "default": "value1"}],
            "input_ports": [{"name": "input1", "type": "string"}],
        }

        unified_path = os.path.join(self.temp_dir, "node_config.json")
        with open(unified_path, "w", encoding="utf-8") as f:
            json.dump(unified_config, f, indent=2, ensure_ascii=False)

        # 测试配置检测
        config_type = ConfigDetector.detect_config_type(self.temp_dir)
        self.assertEqual(config_type, "unified")

        # 测试配置文件列表
        config_files = ConfigDetector.get_config_files(self.temp_dir)
        self.assertIn("node_config.json", config_files)

    def test_merge_legacy_config(self):
        """测试旧格式配置合并"""
        # 创建 config.json
        config = {
            "node_name": "test_node",
            "parameters": [{"name": "param1", "type": "string", "default": "value1"}],
            "input_ports": [{"name": "input1", "type": "string"}],
        }

        config_path = os.path.join(self.temp_dir, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        # 创建 start.json
        start_config = {
            "nodes": [
                {
                    "name": "test_node",
                    "entry": "main.py",
                    "config": {"listen_upper_file": "../data/upper.json", "output_file": "./output.json"},
                }
            ]
        }

        start_path = os.path.join(self.temp_dir, "start.json")
        with open(start_path, "w", encoding="utf-8") as f:
            json.dump(start_config, f, indent=2, ensure_ascii=False)

        # 测试配置检测
        config_type = ConfigDetector.detect_config_type(self.temp_dir)
        self.assertEqual(config_type, "legacy")

        # 测试配置合并
        merged = self.merger.merge_configs(self.temp_dir)

        # 验证合并结果
        self.assertEqual(merged["node_name"], "test_node")
        self.assertEqual(merged["entry"], "main.py")
        self.assertEqual(merged["listen_upper_file"], "../data/upper.json")
        self.assertEqual(merged["output_file"], "./output.json")
        self.assertEqual(len(merged["parameters"]), 1)
        self.assertEqual(merged["parameters"][0]["name"], "param1")
        self.assertEqual(len(merged["input_ports"]), 1)
        self.assertEqual(merged["input_ports"][0]["name"], "input1")

        # 验证备份文件
        backup_path = os.path.join(self.temp_dir, ".config_backup")
        self.assertTrue(os.path.exists(backup_path))

        # 验证统一配置文件
        unified_path = os.path.join(self.temp_dir, "node_config.json")
        self.assertTrue(os.path.exists(unified_path))

    def test_merge_single_node_start_config(self):
        """测试单节点 start.json 格式"""
        # 创建 config.json
        config = {"node_name": "test_node", "parameters": [{"name": "param1", "type": "string", "default": "value1"}]}

        config_path = os.path.join(self.temp_dir, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        # 创建单节点 start.json
        start_config = {"name": "test_node", "entry": "main.py", "config": {"listen_upper_file": "../data/upper.json"}}

        start_path = os.path.join(self.temp_dir, "start.json")
        with open(start_path, "w", encoding="utf-8") as f:
            json.dump(start_config, f, indent=2, ensure_ascii=False)

        # 测试配置合并
        merged = self.merger.merge_configs(self.temp_dir)

        # 验证合并结果
        self.assertEqual(merged["node_name"], "test_node")
        self.assertEqual(merged["entry"], "main.py")
        self.assertEqual(merged["listen_upper_file"], "../data/upper.json")

    def test_config_validation(self):
        """测试配置验证"""
        # 有效配置
        valid_config = {
            "node_name": "test_node",
            "entry": "listener.py",
            "parameters": [{"name": "param1", "type": "string", "default": "value1"}],
            "input_ports": [{"name": "input1", "type": "string"}],
        }

        errors = self.merger.validate_unified_config(valid_config)
        self.assertEqual(len(errors), 0)

        # 无效配置 - 缺少必需字段
        invalid_config = {
            "node_name": "test_node"
            # 缺少 entry
        }

        errors = self.merger.validate_unified_config(invalid_config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("entry" in error for error in errors))

        # 无效配置 - 参数类型错误
        invalid_config = {
            "node_name": "test_node",
            "entry": "listener.py",
            "parameters": [{"name": "param1", "type": "invalid_type"}],
        }

        errors = self.merger.validate_unified_config(invalid_config)
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("invalid_type" in error for error in errors))

    def test_backup_and_restore(self):
        """测试备份和恢复"""
        # 创建配置文件
        config = {"node_name": "test_node"}
        start_config = {"nodes": [{"name": "test_node", "entry": "listener.py"}]}

        with open(os.path.join(self.temp_dir, "config.json"), "w") as f:
            json.dump(config, f)

        with open(os.path.join(self.temp_dir, "start.json"), "w") as f:
            json.dump(start_config, f)

        # 合并配置
        self.merger.merge_configs(self.temp_dir)

        # 验证备份
        backup_path = os.path.join(self.temp_dir, ".config_backup", "config.json")
        self.assertTrue(os.path.exists(backup_path))

        # 恢复配置
        self.merger.restore_legacy_configs(self.temp_dir)

        # 验证恢复
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "config.json")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "start.json")))

    def test_config_detector(self):
        """测试配置检测器"""
        # 无配置文件
        self.assertEqual(ConfigDetector.detect_config_type(self.temp_dir), "none")

        # 只有 config.json
        config_path = os.path.join(self.temp_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump({"node_name": "test_node"}, f)

        self.assertEqual(ConfigDetector.detect_config_type(self.temp_dir), "config_only")

        # 添加 start.json
        start_path = os.path.join(self.temp_dir, "start.json")
        with open(start_path, "w") as f:
            json.dump({"nodes": [{"name": "test_node", "entry": "listener.py"}]}, f)

        self.assertEqual(ConfigDetector.detect_config_type(self.temp_dir), "legacy")

        # 添加 node_config.json
        unified_path = os.path.join(self.temp_dir, "node_config.json")
        with open(unified_path, "w") as f:
            json.dump({"node_name": "test_node", "entry": "listener.py"}, f)

        self.assertEqual(ConfigDetector.detect_config_type(self.temp_dir), "unified")


class TestConfigCompatibility(unittest.TestCase):
    """配置兼容性测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """测试后清理"""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_legacy_config_format(self):
        """测试旧格式配置兼容性"""
        # 创建旧格式配置
        config = {
            "node_name": "python_node",
            "listen_upper_file": "../data/upper_data.json",
            "output_file": "./output.json",
            "filter": {},
            "output_type": "",
            "parameters": [{"name": "param1", "type": "text", "default": "value1", "description": "参数1"}],
            "input_ports": [{"name": "input1", "type": "string", "description": "输入端口1"}],
            "output_ports": [{"name": "output1", "type": "string", "description": "输出端口1"}],
            "port_mappings": {},
            "resource_limit": {"memory_mb": 1024, "cpu_percent": 100},
        }

        config_path = os.path.join(self.temp_dir, "config.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        # 创建 start.json
        start_config = {
            "nodes": [
                {
                    "name": "python_node",
                    "entry": "listener.py",
                    "python_exe": "",
                    "config": {"listen_upper_file": "../data/upper_data.json", "output_file": "./output.json"},
                }
            ]
        }

        start_path = os.path.join(self.temp_dir, "start.json")
        with open(start_path, "w", encoding="utf-8") as f:
            json.dump(start_config, f, indent=2, ensure_ascii=False)

        # 测试配置合并
        merger = ConfigMerger()
        merged = merger.merge_configs(self.temp_dir)

        # 验证合并结果
        self.assertEqual(merged["node_name"], "python_node")
        self.assertEqual(merged["entry"], "listener.py")
        self.assertEqual(merged["listen_upper_file"], "../data/upper_data.json")
        self.assertEqual(merged["output_file"], "./output.json")
        self.assertEqual(merged["python_exe"], "")
        self.assertEqual(len(merged["parameters"]), 1)
        self.assertEqual(merged["parameters"][0]["name"], "param1")
        self.assertEqual(len(merged["input_ports"]), 1)
        self.assertEqual(merged["input_ports"][0]["name"], "input1")
        self.assertEqual(len(merged["output_ports"]), 1)
        self.assertEqual(merged["output_ports"][0]["name"], "output1")
        self.assertEqual(merged["resource_limit"]["memory_mb"], 1024)
        self.assertEqual(merged["resource_limit"]["cpu_percent"], 100)

        # 验证参数和端口
        self.assertEqual(len(merged["parameters"]), 1)
        self.assertEqual(merged["parameters"][0]["name"], "param1")
        self.assertEqual(len(merged["input_ports"]), 1)
        self.assertEqual(merged["input_ports"][0]["name"], "input1")
        self.assertEqual(len(merged["output_ports"]), 1)
        self.assertEqual(merged["output_ports"][0]["name"], "output1")

        # 验证统一配置文件
        unified_path = os.path.join(self.temp_dir, "node_config.json")
        self.assertTrue(os.path.exists(unified_path))

        # 验证备份文件
        backup_path = os.path.join(self.temp_dir, ".config_backup")
        self.assertTrue(os.path.exists(backup_path))

        # 验证备份内容
        backup_config = os.path.join(backup_path, "config.json")
        backup_start = os.path.join(backup_path, "start.json")
        self.assertTrue(os.path.exists(backup_config))
        self.assertTrue(os.path.exists(backup_start))


if __name__ == "__main__":
    unittest.main()

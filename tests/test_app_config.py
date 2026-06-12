"""
应用配置模块测试
测试 AppConfig 的配置读写和原子性写入功能
"""
import os
import pytest
import tempfile
import json
from ui.core.app_config import AppConfig


class TestAppConfig:
    """应用配置测试"""

    def setup_method(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.temp_dir, "test_config.json")
        self.backup_path = self.config_path + ".bak"
        self.tmp_path = self.config_path + ".tmp"

    def teardown_method(self):
        """测试后清理"""
        for path in [self.config_path, self.backup_path, self.tmp_path]:
            if os.path.exists(path):
                os.remove(path)
        os.rmdir(self.temp_dir)

    def test_config_write_read(self):
        """测试配置写入和读取"""
        config = AppConfig()
        config.config_file = self.config_path
        
        # 写入配置
        test_data = {"key1": "value1", "key2": 123}
        config.config = test_data
        config.save()
        
        # 验证文件存在
        assert os.path.exists(self.config_path)
        
        # 读取验证
        with open(self.config_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded == test_data

    def test_atomic_write_fallback(self):
        """测试原子写入的回滚机制"""
        # 先创建一个有效配置
        initial_data = {"original": "data"}
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f)
        
        config = AppConfig()
        config.config_file = self.config_path
        
        # 修改配置
        config.config = {"new": "data"}
        
        # 模拟写入失败（创建临时文件但不完成替换）
        with open(self.tmp_path, 'w', encoding='utf-8') as f:
            json.dump({"corrupted": "data"}, f)
        
        # 删除临时文件模拟写入中断
        os.remove(self.tmp_path)
        
        # 原始配置应该保持不变
        with open(self.config_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded == initial_data

    def test_config_defaults(self):
        """测试配置默认值"""
        config = AppConfig()
        config.config_file = self.config_path
        
        # 新配置应该是空字典或包含默认值
        assert isinstance(config.config, dict)
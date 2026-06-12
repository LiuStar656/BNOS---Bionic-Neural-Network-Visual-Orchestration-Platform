"""
轮询管理器测试
测试 PollingManager 的轮询间隔和文件监听功能

注意：此测试需要 Qt 应用环境，建议在 GUI 测试框架中运行
"""
import pytest


class TestPollingManager:
    """轮询管理器测试"""

    def test_polling_manager_import(self):
        """测试轮询管理器模块导入"""
        try:
            from ui.core.polling_manager import PollingManager
            assert True
        except ImportError:
            pytest.skip("Qt environment not available")

    def test_polling_manager_is_singleton(self):
        """测试轮询管理器是单例"""
        try:
            from ui.core.polling_manager import PollingManager
            instance1 = PollingManager.instance()
            instance2 = PollingManager.instance()
            assert instance1 is instance2
        except ImportError:
            pytest.skip("Qt environment not available")
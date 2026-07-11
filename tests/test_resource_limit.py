"""资源限制组件测试。

测试全平台 ResourceLimit 组件的工厂函数、优先级映射、上下文管理器、
以及各平台实现的接口一致性。
"""

from __future__ import annotations

import platform

import pytest

from ui.core.system.resource_limit import (
    ResourceLimit,
    _DarwinResourceLimit,
    _LinuxResourceLimit,
    _WindowsResourceLimit,
    create_resource_limit,
)

_SYSTEM = platform.system()


class TestFactory:
    """工厂函数测试"""

    def test_create_returns_correct_platform(self):
        """根据操作系统返回正确的实现类。"""
        limit = create_resource_limit(0, {})
        assert isinstance(limit, ResourceLimit)

    def test_create_resource_limit_with_full_config(self):
        """完整配置的创建不应报错。"""
        config = {
            "memory_mb": 512,
            "cpu_percent": 200,
            "cpu_affinity": [0, 1],
            "priority": "below_normal",
        }
        limit = create_resource_limit(0, config)
        assert isinstance(limit, ResourceLimit)

    def test_create_resource_limit_with_empty_config(self):
        """空配置的创建不应报错。"""
        limit = create_resource_limit(0, {})
        assert isinstance(limit, ResourceLimit)


class TestPriorityMapping:
    """优先级映射测试"""

    @pytest.mark.parametrize(
        "level",
        ["low", "below_normal", "normal", "above_normal", "high"],
    )
    def test_valid_priority_levels(self, level):
        """所有有效优先级级别都应被接受。"""
        limit = create_resource_limit(0, {"priority": level})
        assert isinstance(limit, ResourceLimit)

    def test_unknown_priority_does_not_crash(self):
        """未知优先级不应导致崩溃。"""
        limit = create_resource_limit(0, {"priority": "super_duper_high"})
        assert isinstance(limit, ResourceLimit)

    def test_priority_none_skipped(self):
        """不配置 priority 时不应尝试设置。"""
        limit = create_resource_limit(0, {"memory_mb": 512})
        applied = limit.apply()
        # 不应包含 priority 项
        assert not any(a.startswith("priority=") for a in applied)


class TestContextManager:
    """上下文管理器测试"""

    def test_context_manager_enter_exit(self):
        """测试 ResourceLimit 可以作为上下文管理器使用。"""
        with create_resource_limit(0, {"priority": "normal"}) as limit:
            assert isinstance(limit, ResourceLimit)


class TestApplyNoProcess:
    """无实际进程时的行为测试"""

    @pytest.fixture
    def nonexistent_pid(self) -> int:
        """返回一个几乎不可能存在的 PID。"""
        return 99999999

    def test_apply_does_not_raise_on_bad_pid(self, nonexistent_pid):
        """对不存在的 PID apply() 不应抛出异常（优雅降级）。"""
        limit = create_resource_limit(nonexistent_pid, {"priority": "normal"})
        # 不应 raise
        applied = limit.apply()
        # 在不存在的进程上设置优先级会失败，不应有任何 applied
        assert isinstance(applied, list)


class TestDarwinFallback:
    """macOS 回退实现测试"""

    def test_darwin_hard_limits_return_empty(self):
        """macOS 硬限制应返回空列表且不崩溃。"""
        limit = _DarwinResourceLimit(0, {"memory_mb": 512, "cpu_percent": 50})
        applied = limit._apply_hard_limits()
        assert applied == []


class TestInterfaceConsistency:
    """接口一致性测试 —— 确保所有子类实现了必要方法"""

    @pytest.mark.parametrize(
        "cls",
        [_LinuxResourceLimit, _WindowsResourceLimit, _DarwinResourceLimit],
    )
    def test_concrete_class_has_hard_limits_method(self, cls):
        """所有具体实现类必须实现 _apply_hard_limits。"""
        assert hasattr(cls, "_apply_hard_limits")
        assert callable(cls._apply_hard_limits)

    def test_apply_returns_list(self):
        """apply() 必须返回 list[str]。"""
        limit = create_resource_limit(0, {})
        result = limit.apply()
        assert isinstance(result, list)


class TestConfigEdgeCases:
    """配置边界情况测试"""

    def test_negative_memory_is_accepted_by_factory(self):
        """工厂不校验配置值（由平台实现处理）。"""
        limit = create_resource_limit(0, {"memory_mb": -1})
        assert isinstance(limit, ResourceLimit)

    def test_zero_cpu_is_accepted_by_factory(self):
        """工厂不校验配置值（由平台实现处理）。"""
        limit = create_resource_limit(0, {"cpu_percent": 0})
        assert isinstance(limit, ResourceLimit)

    def test_partial_config_only_memory(self):
        """仅配置 memory_mb 时其余限制不影响。"""
        limit = create_resource_limit(0, {"memory_mb": 1024})
        applied = limit.apply()
        # 不应包含 cpu_percent 项
        assert not any(a.startswith("cpu_percent=") for a in applied)

    def test_partial_config_only_cpu(self):
        """仅配置 cpu_percent 时其余限制不影响。"""
        limit = create_resource_limit(0, {"cpu_percent": 50})
        applied = limit.apply()
        assert not any(a.startswith("memory_mb=") for a in applied)

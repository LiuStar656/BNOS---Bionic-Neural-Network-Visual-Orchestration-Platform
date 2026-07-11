"""
依赖注入容器测试
测试 DIContainer 的服务注册和解析功能（含旧 API 兼容 + 新 API）
"""
import pytest
from ui.core.system.di import DIContainer


# ======================== 原有测试（向后兼容验证）========================

class TestDIContainerBackwardCompat:
    """验证原有 register_instance / register_factory / resolve / is_registered 仍然可用"""

    def test_register_instance_and_resolve(self):
        di = DIContainer()

        class TestService:
            def __init__(self):
                self.value = 42

        instance = TestService()
        di.register_instance(TestService, instance)
        resolved = di.resolve(TestService)
        assert resolved is instance
        assert resolved.value == 42

    def test_register_factory_and_resolve(self):
        di = DIContainer()

        class TestService:
            def __init__(self):
                self.value = 100

        di.register_factory(TestService, TestService)
        resolved = di.resolve(TestService)
        assert isinstance(resolved, TestService)
        assert resolved.value == 100

    def test_resolve_singleton(self):
        di = DIContainer()

        class CounterService:
            def __init__(self):
                self.count = 0

        di.register_factory(CounterService, CounterService)
        service1 = di.resolve(CounterService)
        service2 = di.resolve(CounterService)
        assert service1 is service2

    def test_resolve_nonexistent_service(self):
        di = DIContainer()

        class NonexistentService:
            pass

        with pytest.raises(KeyError):
            di.resolve(NonexistentService)

    def test_is_registered_by_type(self):
        di = DIContainer()

        class TestService:
            pass

        assert di.is_registered(TestService) is False
        di.register_instance(TestService, TestService())
        assert di.is_registered(TestService) is True

    def test_register_multiple_services(self):
        di = DIContainer()

        class ServiceA:
            pass

        class ServiceB:
            pass

        di.register_instance(ServiceA, ServiceA())
        di.register_instance(ServiceB, ServiceB())
        assert isinstance(di.resolve(ServiceA), ServiceA)
        assert isinstance(di.resolve(ServiceB), ServiceB)


# ======================== 新 API 测试 ========================

class TestNewRegisterAPI:
    """测试统一 register() 方法和增强 resolve()"""

    def test_register_with_string_name(self):
        di = DIContainer()

        class MyService:
            def __init__(self, label=""):
                self.label = label

        svc = MyService("hello")
        di.register(MyService, svc, name="primary")
        resolved = di.resolve(MyService, name="primary")
        assert resolved is svc
        assert resolved.label == "hello"

    def test_resolve_by_name_string(self):
        di = DIContainer()
        di.register(str, 42, name="answer")
        assert di.resolve("answer") == 42

    def test_resolve_named_convenience(self):
        di = DIContainer()
        di.register(str, "data", name="payload")
        assert di.resolve_named("payload") == "data"

    def test_is_registered_by_string_name(self):
        di = DIContainer()
        assert di.is_registered("logger") is False
        di.register(str, "logger_impl", name="logger")
        assert di.is_registered("logger") is True

    def test_is_registered_by_type_and_name(self):
        di = DIContainer()

        class Svc:
            pass

        di.register(Svc, Svc(), name="a")
        assert di.is_registered(Svc, name="a") is True
        assert di.is_registered(Svc, name="b") is False

    def test_transient_scope(self):
        di = DIContainer()
        counter = [0]

        def factory():
            counter[0] += 1
            return counter[0]

        di.register(int, factory, scope="transient")
        a = di.resolve(int)
        b = di.resolve(int)
        assert a == 1
        assert b == 2
        assert a != b

    def test_singleton_scope_explicit(self):
        di = DIContainer()
        counter = [0]

        def factory():
            counter[0] += 1
            return counter[0]

        di.register(int, factory, scope="singleton")
        a = di.resolve(int)
        b = di.resolve(int)
        assert a == 1
        assert b == 1
        assert a == b

    def test_invalid_scope_raises(self):
        di = DIContainer()
        with pytest.raises(ValueError, match="scope"):
            di.register(int, 1, scope="per_request")

    def test_multiple_implementations_same_type(self):
        di = DIContainer()

        class ILogger:
            pass

        class FileLogger(ILogger):
            pass

        class ConsoleLogger(ILogger):
            pass

        f = FileLogger()
        c = ConsoleLogger()
        di.register(ILogger, f, name="file")
        di.register(ILogger, c, name="console")

        assert di.resolve(ILogger, name="file") is f
        assert di.resolve(ILogger, name="console") is c


class TestListRegistered:
    """测试 list_registered() 查询功能"""

    def test_empty_container(self):
        di = DIContainer()
        assert di.list_registered() == []

    def test_lists_all_entries(self):
        di = DIContainer()
        di.register_instance(int, 1)
        di.register(str, "val", name="s")
        di.register(float, lambda: 3.14, scope="transient")
        result = di.list_registered()
        assert len(result) == 3
        types = {r[0] for r in result}
        assert types == {int, str, float}


class TestErrorMessage:
    """测试未注册时的错误提示"""

    def test_error_includes_available_services(self):
        di = DIContainer()

        class Foo:
            pass

        di.register(Foo, Foo(), name="foo")
        with pytest.raises(KeyError) as exc_info:
            di.resolve(str)
        msg = str(exc_info.value)
        assert "未注册" in msg
        assert "Foo" in msg
        assert "foo" in msg

    def test_error_for_unknown_name(self):
        di = DIContainer()
        with pytest.raises(KeyError) as exc_info:
            di.resolve("nonexistent")
        assert "未注册" in str(exc_info.value)

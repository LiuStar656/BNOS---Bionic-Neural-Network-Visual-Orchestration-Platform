"""
依赖注入容器测试
测试 DIContainer 的服务注册和解析功能
"""
import pytest
from ui.core.di import DIContainer


class TestDIContainer:
    """依赖注入容器测试"""

    def test_register_instance_and_resolve(self):
        """测试注册实例和解析"""
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
        """测试注册工厂和解析"""
        di = DIContainer()
        
        class TestService:
            def __init__(self):
                self.value = 100
        
        di.register_factory(TestService, TestService)
        
        resolved = di.resolve(TestService)
        assert isinstance(resolved, TestService)
        assert resolved.value == 100

    def test_resolve_singleton(self):
        """测试单例解析"""
        di = DIContainer()
        
        class CounterService:
            def __init__(self):
                self.count = 0
        
        di.register_factory(CounterService, CounterService)
        
        service1 = di.resolve(CounterService)
        service2 = di.resolve(CounterService)
        
        assert service1 is service2

    def test_resolve_nonexistent_service(self):
        """测试解析不存在的服务"""
        di = DIContainer()
        
        class NonexistentService:
            pass
        
        with pytest.raises(KeyError):
            di.resolve(NonexistentService)

    def test_is_registered(self):
        """测试服务存在性检查"""
        di = DIContainer()
        
        class TestService:
            pass
        
        assert di.is_registered(TestService) is False
        
        di.register_instance(TestService, TestService())
        assert di.is_registered(TestService) is True

    def test_register_multiple_services(self):
        """测试注册多个服务"""
        di = DIContainer()
        
        class ServiceA:
            pass
        
        class ServiceB:
            pass
        
        di.register_instance(ServiceA, ServiceA())
        di.register_instance(ServiceB, ServiceB())
        
        assert isinstance(di.resolve(ServiceA), ServiceA)
        assert isinstance(di.resolve(ServiceB), ServiceB)
"""
事件总线模块测试
测试 EventBus 的发布/订阅机制
"""
import pytest
from ui.core.event_bus import event_bus, EventBus


class TestEventBus:
    """事件总线测试"""

    def test_subscribe_and_publish(self):
        """测试订阅和发布事件"""
        received_events = []
        
        def handler(event_data):
            received_events.append(event_data)
        
        # 订阅事件
        event_bus.subscribe("test.event", handler)
        
        # 发布事件
        test_data = {"key": "value"}
        event_bus.publish("test.event", test_data)
        
        # 验证事件收到
        assert len(received_events) == 1
        assert received_events[0] == test_data
        
        # 清理订阅
        event_bus.unsubscribe("test.event", handler)

    def test_multiple_subscribers(self):
        """测试多个订阅者"""
        counter1 = [0]
        counter2 = [0]
        
        def handler1(_):
            counter1[0] += 1
        
        def handler2(_):
            counter2[0] += 1
        
        # 订阅同一事件
        event_bus.subscribe("test.multiple", handler1)
        event_bus.subscribe("test.multiple", handler2)
        
        # 发布事件
        event_bus.publish("test.multiple", {})
        
        # 验证两个订阅者都收到
        assert counter1[0] == 1
        assert counter2[0] == 1
        
        # 清理
        event_bus.unsubscribe("test.multiple", handler1)
        event_bus.unsubscribe("test.multiple", handler2)

    def test_unsubscribe(self):
        """测试取消订阅"""
        counter = [0]
        
        def handler(_):
            counter[0] += 1
        
        event_bus.subscribe("test.unsubscribe", handler)
        event_bus.publish("test.unsubscribe", {})
        assert counter[0] == 1
        
        # 取消订阅
        event_bus.unsubscribe("test.unsubscribe", handler)
        
        # 再次发布，不应收到
        event_bus.publish("test.unsubscribe", {})
        assert counter[0] == 1

    def test_no_subscribers(self):
        """测试向无订阅者发布事件"""
        # 应该不会报错
        event_bus.publish("test.no_subscribers", {"data": "test"})

    def test_event_data_types(self):
        """测试不同类型的事件数据"""
        received = []
        
        def handler(data):
            received.append(data)
        
        event_bus.subscribe("test.types", handler)
        
        # 发布不同类型的数据
        event_bus.publish("test.types", "string_data")
        event_bus.publish("test.types", 123)
        event_bus.publish("test.types", {"key": "value"})
        event_bus.publish("test.types", [1, 2, 3])
        
        assert received == ["string_data", 123, {"key": "value"}, [1, 2, 3]]
        
        event_bus.unsubscribe("test.types", handler)
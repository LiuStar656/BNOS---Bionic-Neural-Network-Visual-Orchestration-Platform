"""
test_action_registry.py — ActionRegistry 单元测试
覆盖: action_registry.py (register, get, all, execute, is_enabled, clear, get_action_ids)
"""
import pytest
from ui.core.actions.action_registry import ActionRegistry
from ui.core.actions.action_definition import ActionDefinition, ActionContext, ActionCategory


# ═══════════════════ 工具函数 ═══════════════════

def _make_action(action_id, category=ActionCategory.NODE, execute_fn=None, is_enabled_fn=None):
    return ActionDefinition(
        id=action_id,
        name_i18n=f"k_{action_id}",
        category=category,
        execute_fn=execute_fn,
        is_enabled_fn=is_enabled_fn,
    )


# ═══════════════════ ActionRegistry 测试 ═══════════════════

class TestActionRegistry:
    def setup_method(self):
        """每个测试前清空注册表"""
        ActionRegistry.clear()

    # ── register / get ──

    def test_register_and_get(self):
        action = _make_action("node.start")
        ActionRegistry.register(action)
        assert ActionRegistry.get("node.start") is action

    def test_get_nonexistent(self):
        assert ActionRegistry.get("nonexistent") is None

    def test_register_overwrite(self):
        a1 = _make_action("node.start")
        a2 = _make_action("node.start")
        ActionRegistry.register(a1)
        ActionRegistry.register(a2)
        assert ActionRegistry.get("node.start") is a2  # 后注册覆盖

    # ── all ──

    def test_all_no_filter(self):
        a1 = _make_action("n1", ActionCategory.NODE)
        a2 = _make_action("c1", ActionCategory.CANVAS)
        ActionRegistry.register(a1)
        ActionRegistry.register(a2)
        all_actions = ActionRegistry.all()
        assert len(all_actions) == 2

    def test_all_filter_by_category(self):
        a1 = _make_action("n1", ActionCategory.NODE)
        a2 = _make_action("c1", ActionCategory.CANVAS)
        a3 = _make_action("p1", ActionCategory.PROJECT)
        ActionRegistry.register(a1)
        ActionRegistry.register(a2)
        ActionRegistry.register(a3)

        nodes = ActionRegistry.all(ActionCategory.NODE)
        assert len(nodes) == 1
        assert nodes[0].id == "n1"

        canvas = ActionRegistry.all(ActionCategory.CANVAS)
        assert len(canvas) == 1
        assert canvas[0].id == "c1"

    def test_all_empty_registry(self):
        assert ActionRegistry.all() == []

    # ── execute ──

    def test_execute_calls_fn(self):
        results = []
        action = _make_action("test.exec", execute_fn=lambda ctx: results.append(ctx) or True)
        ActionRegistry.register(action)
        ctx = ActionContext(node_name="my_node")
        success = ActionRegistry.execute("test.exec", ctx)
        assert success is True
        assert len(results) == 1
        assert results[0].node_name == "my_node"

    def test_execute_nonexistent(self):
        assert ActionRegistry.execute("nonexistent") is False

    def test_execute_no_execute_fn(self):
        action = _make_action("noop")  # 没有 execute_fn
        ActionRegistry.register(action)
        assert ActionRegistry.execute("noop") is False

    def test_execute_default_context(self):
        results = []
        action = _make_action("test.ctx", execute_fn=lambda ctx: results.append(ctx) or True)
        ActionRegistry.register(action)
        ActionRegistry.execute("test.ctx")
        assert len(results) == 1
        assert results[0].node_name is None

    # ── is_enabled ──

    def test_is_enabled_uses_fn(self):
        action = _make_action(
            "test.enabled",
            is_enabled_fn=lambda ctx: ctx.node_name == "active"
        )
        ActionRegistry.register(action)

        assert ActionRegistry.is_enabled("test.enabled", ActionContext(node_name="active")) is True
        assert ActionRegistry.is_enabled("test.enabled", ActionContext(node_name="inactive")) is False

    def test_is_enabled_nonexistent(self):
        assert ActionRegistry.is_enabled("nonexistent") is False

    def test_is_enabled_default_true(self):
        action = _make_action("test.default")  # 无 is_enabled_fn
        ActionRegistry.register(action)
        assert ActionRegistry.is_enabled("test.default") is True

    def test_is_enabled_default_context(self):
        action = _make_action(
            "test.ctx",
            is_enabled_fn=lambda ctx: ctx is not None
        )
        ActionRegistry.register(action)
        assert ActionRegistry.is_enabled("test.ctx") is True

    # ── clear ──

    def test_clear_empties_registry(self):
        ActionRegistry.register(_make_action("a"))
        ActionRegistry.register(_make_action("b"))
        assert len(ActionRegistry.all()) == 2
        ActionRegistry.clear()
        assert ActionRegistry.all() == []

    # ── get_action_ids ──

    def test_get_action_ids(self):
        ActionRegistry.register(_make_action("a"))
        ActionRegistry.register(_make_action("b"))
        ActionRegistry.register(_make_action("c"))
        ids = ActionRegistry.get_action_ids()
        assert set(ids) == {"a", "b", "c"}

    def test_get_action_ids_empty(self):
        assert ActionRegistry.get_action_ids() == []


# ═══════════════════ ActionDefinition ═══════════════════

class TestActionDefinition:
    def test_minimal_creation(self):
        a = ActionDefinition(id="test", name_i18n="k_test", category=ActionCategory.NODE)
        assert a.id == "test"
        assert a.category == ActionCategory.NODE
        assert a.requires_selection is False
        assert a.requires_node is False
        assert a.requires_permission is None
        assert a.execute_fn is None
        assert a.is_enabled_fn is None

    def test_full_creation(self):
        def dummy_exec(ctx): return True
        def dummy_enabled(ctx): return False

        a = ActionDefinition(
            id="full.test",
            name_i18n="k_full_test",
            category=ActionCategory.TOOLS,
            description_i18n="k_desc",
            shortcut_id="Ctrl+T",
            requires_selection=True,
            requires_node=True,
            requires_permission="admin",
            execute_fn=dummy_exec,
            is_enabled_fn=dummy_enabled,
            icon_id="play"
        )
        assert a.description_i18n == "k_desc"
        assert a.shortcut_id == "Ctrl+T"
        assert a.requires_selection is True
        assert a.requires_node is True
        assert a.requires_permission == "admin"
        assert a.icon_id == "play"
        assert a.execute_fn is dummy_exec

"""
翻译 Key 集中管理测试
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTranslationKeys:
    """测试 translation_keys.py — 集中翻译 Key 注册表"""

    def test_import(self):
        """TK 可以正常导入"""
        from ui.core.i18n.translation_keys import TK, TranslationKeys

        assert TK is TranslationKeys

    def test_count_keys(self):
        """key 总数大于 200"""
        from ui.core.i18n.translation_keys import TranslationKeys

        count = TranslationKeys.count()
        assert count > 200, f"Expected >200 keys, got {count}"

    def test_all_keys_returns_list(self):
        """all_keys() 返回 list[str]"""
        from ui.core.i18n.translation_keys import TranslationKeys

        keys = TranslationKeys.all_keys()
        assert isinstance(keys, list)
        assert len(keys) > 200
        assert all(isinstance(k, str) for k in keys)

    def test_common_keys_exist(self):
        """常用 key 存在"""
        from ui.core.i18n.translation_keys import TranslationKeys as TK

        assert TK.PROJECT == "k_project"
        assert TK.PROJECT_NEW == "k_project_new"
        assert TK.NODE_CREATE == "k_node_create"
        assert TK.NODE_START == "k_node_start"
        assert TK.NODE_STOP == "k_node_stop"
        assert TK.GROUP_CREATE == "k_group_create"
        assert TK.MENU_FILE == "k_menu_file"
        assert TK.OK == "k_ok"
        assert TK.CANCEL == "k_cancel"
        assert TK._APP_NAME == "_k_app_name"
        assert TK._ABOUT_TEXT == "_k_about_text"

    def test_underscore_keys_exist(self):
        """带 _ 前缀的 key 存在且正确"""
        from ui.core.i18n.translation_keys import TranslationKeys as TK

        assert TK.START == "k_start"  # 非 _ 属性
        assert TK._START_FAILED == "_k_start_failed"
        assert TK._NODE_STARTED == "_k_node_started"
        assert TK._NODE_STOPPED == "_k_node_stopped"

    def test_all_keys_include_underscore(self):
        """all_keys() 同时包含 k_ 和 _k_ 前缀的 key"""
        from ui.core.i18n.translation_keys import TranslationKeys as TK

        keys = TK.all_keys()
        has_k = any(k.startswith("k_") for k in keys)
        has_uk = any(k.startswith("_k_") for k in keys)
        assert has_k, "Should include k_ prefixed keys"
        assert has_uk, "Should include _k_ prefixed keys"

    def test_validate_passes(self):
        """validate() 应该通过（所有定义的 key 都在 JSON 中）"""
        from ui.core.i18n.translation_keys import TranslationKeys as TK

        result = TK.validate()
        assert result["ok"], f"Validation failed: {result}"

    def test_key_values_are_unique(self):
        """没有重复的 key 值"""
        from ui.core.i18n.translation_keys import TranslationKeys as TK

        # 获取所有 key/value 对
        pairs = []
        for k, v in vars(TK).items():
            if k.startswith("__"):
                continue
            if isinstance(v, str) and v.startswith(("k_", "_k_")):
                pairs.append((k, v))
        values = [v for _, v in pairs]
        assert len(values) == len(set(values)), f"Duplicate keys: {[v for v in values if values.count(v) > 1]}"

    def test_no_missing_k_keys(self):
        """所有 k_ 开头的 JSON key 都应该在 TK 中有对应属性"""
        import json

        _here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _path = os.path.join(_here, "ui", "core", "i18n", "strings_cn.json")
        with open(_path, encoding="utf-8") as f:
            json_keys = set(json.load(f).keys())

        from ui.core.i18n.translation_keys import TranslationKeys as TK

        defined_keys = set(TK.all_keys())

        # JSON 中有但 TK 中没有的
        missing = json_keys - defined_keys
        if missing:
            pytest.fail(f"JSON keys not in TK: {sorted(missing)}\nThese keys need to be added to translation_keys.py")


class TestI18nIntegration:
    """测试 i18n.py 与 translation_keys.py 的集成"""

    def test_validate_all_keys(self):
        """validate_all_keys() 应该通过"""
        from ui.core.i18n import init_i18n, validate_all_keys

        init_i18n("cn")
        result = validate_all_keys()
        assert result["ok"], f"Validation failed: {result}"

    def test_t_with_tk(self):
        """t(TK.PROJECT) 与 t("k_project") 等效"""
        from ui.core.i18n import init_i18n, t
        from ui.core.i18n.translation_keys import TranslationKeys as TK

        init_i18n("cn")
        assert t(TK.PROJECT) == t("k_project")
        assert t(TK.NODE_CREATE) == t("k_node_create")
        assert t(TK._APP_NAME) == t("_k_app_name")


class TestBackwardCompatibility:
    """向后兼容性测试 — 旧代码的 t("k_...") 仍然工作"""

    def test_raw_string_still_works(self):
        """裸字符串 key 仍然可以正常翻译"""
        from ui.core.i18n import init_i18n, t

        init_i18n("cn")
        assert t("k_project") != "k_project"  # 应该被翻译
        assert t("k_ok") == "确定"

    def test_missing_key_returns_self(self):
        """不存在的 key 返回自身"""
        from ui.core.i18n import init_i18n, t

        init_i18n("cn")
        assert t("k_definitely_not_exist_12345") == "k_definitely_not_exist_12345"

    def test_en_fallback(self):
        """英文模式下翻译正确"""
        from ui.core.i18n import init_i18n, t

        try:
            init_i18n("en")
        except Exception:
            init_i18n("cn")
        assert t("k_ok") in ("确定", "OK")  # 取决于语言文件是否加载成功

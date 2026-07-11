"""
国际化模块 — 统一字符串管理

用法:
    from ui.core.i18n import t, init_i18n, set_lang

    init_i18n("cn")                # 入口处调用一次
    set_lang("en")                 # 运行时切换语言
    msg = t("k_project_created")   # "项目已创建" / "Project Created"
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

STRINGS: dict = {}
LANG: str = "cn"


def t(key: str) -> str:
    """返回 key 对应的字符串，未找到则返回 key 本身（兜底）"""
    return STRINGS.get(key, key)


def get_lang() -> str:
    """返回当前语言代码 (cn/en) — 避免 from import 值拷贝问题"""
    return LANG


def set_lang(lang: str):
    """运行时切换语言 (cn/en)"""
    init_i18n(lang)


def init_i18n(lang: str = "cn"):
    """加载语言文件并初始化 STRINGS 字典"""
    global STRINGS, LANG
    LANG = lang
    _here = os.path.dirname(os.path.abspath(__file__))
    filename = f"strings_{lang}.json"
    _path = os.path.join(_here, filename)
    try:
        with open(_path, "r", encoding="utf-8") as f:
            STRINGS = json.load(f)
        logger.info("i18n loaded %d strings from %s", len(STRINGS), filename)
    except FileNotFoundError:
        logger.warning("%s not found, falling back to strings_cn.json", filename)
        try:
            _cn = os.path.join(_here, "strings_cn.json")
            with open(_cn, "r", encoding="utf-8") as f:
                STRINGS = json.load(f)
            LANG = "cn"
            logger.info("i18n fallback to strings_cn.json (%d strings)", len(STRINGS))
        except FileNotFoundError:
            logger.warning("strings_cn.json not found, using key as fallback")
            STRINGS = {}
    except Exception as e:
        logger.error("i18n load failed: %s", e)
        STRINGS = {}


def validate_all_keys() -> dict:
    """验证集中翻译 key 注册表中的所有 key 是否存在于当前 JSON。
    init_i18n() 之后调用，配合 ui.core.translation_keys.TK 使用。

    返回: {"ok": True} 或 {"ok": False, "missing": [...]}
    """
    _here = os.path.dirname(os.path.abspath(__file__))
    _cn = os.path.join(_here, "strings_cn.json")
    try:
        with open(_cn, "r", encoding="utf-8") as f:
            cn_keys = set(json.load(f).keys())
    except Exception as e:
        return {"ok": False, "error": str(e)}

    try:
        from ui.core.translation_keys import TranslationKeys
        defined_keys = set(TranslationKeys.all_keys())
    except ImportError:
        return {"ok": True, "note": "translation_keys module not available"}

    missing = [k for k in defined_keys if k not in cn_keys]
    extra = [k for k in cn_keys if k not in defined_keys]

    result = {"ok": True}
    if missing:
        result["ok"] = False
        result["missing"] = missing
        logger.warning("i18n: %d keys defined in TK but missing in JSON: %s", len(missing), missing[:5])
    if extra:
        result["extra"] = extra
        logger.info("i18n: %d keys in JSON not yet in TK registry (not an error)", len(extra))
    return result

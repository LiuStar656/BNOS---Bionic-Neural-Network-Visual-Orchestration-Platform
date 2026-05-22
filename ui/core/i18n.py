"""
国际化模块 — 统一字符串管理

用法:
    from ui.core.i18n import t, init_i18n

    init_i18n()                    # 入口处调用一次
    msg = t("k_project_created")   # "项目已创建"
"""
import os
import json
import logging

logger = logging.getLogger(__name__)

STRINGS: dict = {}


def t(key: str) -> str:
    """返回 key 对应的中文字符串，未找到则返回 key 本身（兜底）"""
    return STRINGS.get(key, key)


def init_i18n():
    """加载 strings_cn.json 并初始化 STRINGS 字典"""
    global STRINGS
    _here = os.path.dirname(os.path.abspath(__file__))
    _path = os.path.join(_here, "strings_cn.json")
    try:
        with open(_path, "r", encoding="utf-8") as f:
            STRINGS = json.load(f)
        logger.info("i18n 已加载 %d 条字符串", len(STRINGS))
    except FileNotFoundError:
        logger.warning("strings_cn.json 未找到，使用 key 作为兜底")
        STRINGS = {}
    except Exception as e:
        logger.error("i18n 加载失败: %s", e)
        STRINGS = {}

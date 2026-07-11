"""Internationalization: translation engine, key registry, string files.

This __init__ re-exports from i18n.py so that all existing:
    from ui.core.i18n import t
continue to work transparently.
"""

from ui.core.i18n.i18n import (
    STRINGS,
    LANG,
    t,
    get_lang,
    set_lang,
    init_i18n,
    validate_all_keys,
)

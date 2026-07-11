"""Internationalization: translation engine, key registry, string files.

This __init__ re-exports from i18n.py so that all existing:
    from ui.core.i18n import t
continue to work transparently.
"""

from __future__ import annotations

from ui.core.i18n.i18n import (
    LANG,
    STRINGS,
    get_lang,
    init_i18n,
    set_lang,
    t,
    validate_all_keys,
)

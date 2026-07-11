"""
测试终端 Dock 功能 - 简单验证
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


# 测试导入
try:
    pass
except Exception:
    sys.exit(1)

try:
    pass
except Exception:
    sys.exit(1)

try:
    pass
except Exception:
    sys.exit(1)

try:
    pass

    # 测试翻译
except Exception:
    sys.exit(1)

try:
    from ui.core.config.app_config import AppConfig

    config = AppConfig()
except Exception:
    sys.exit(1)

files = [
    "ui/core/terminal/__init__.py",
    "ui/core/terminal/terminal_process.py",
    "ui/core/terminal/terminal_widget.py",
    "ui/core/terminal/terminal_dock.py",
]
for f in files:
    if os.path.exists(f):
        pass
    else:
        pass

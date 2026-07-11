from __future__ import annotations

import ast

files = [
    "ui/panels/node_list_dock.py",
    "ui/main_window/panel.py",
    "ui/main_window/state.py",
    "ui/core/project/project_manager.py",
    "ui/main_window/__main__.py",
    "ui/main_window/lifecycle.py",
    "ui/panels/node_list_panel.py",
    "bnos_console.py",
]
for f in files:
    try:
        with open(f, encoding="utf-8") as fp:
            ast.parse(fp.read())
    except Exception:
        pass

"""
节点操作功能模块 — 按功能组拆分为独立子模块

子模块：
  _lifecycle   — start/stop/config/refresh/mount/export（6 个 action）
  _context_menu — add_to_canvas/open_folder/view_log/edit_config/rename/delete/unmount（7 个 action）
  _batch       — 5 个 batch_* action
  _selection   — select_all/deselect_all（2 个 action）
  _group       — 10 个 group.* action
  _ungrouped   — ungrouped.*（2 个 action）
  _ide         — open_vscode/open_trae_ide（2 个 action）
  _style       — change_style/change_bg_color/change_border_color/change_text_color（4 个 action）
"""
from . import _lifecycle
from . import _context_menu
from . import _batch
from . import _selection
from . import _group
from . import _ungrouped
from . import _ide
from . import _style


def register_node_actions(main_window):
    """注册全部节点相关功能（汇总调用各子模块）"""
    modules = [
        _lifecycle,
        _context_menu,
        _batch,
        _selection,
        _group,
        _ungrouped,
        _ide,
        _style,
    ]
    for mod in modules:
        mod.register(main_window)

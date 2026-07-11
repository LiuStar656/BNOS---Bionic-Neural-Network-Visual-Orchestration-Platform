"""预设节点库 — save_as_preset / open_preset_library"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..action_definition import ActionCategory, ActionContext, ActionDefinition
from ..action_registry import ActionRegistry


def register(main_window):
    """注册预设节点相关 action"""
    _register_save_as_preset(main_window)
    _register_open_preset_library(main_window)


def _register_save_as_preset(main_window):
    """注册"保存为预设节点"功能 — 复用 .bnos 导出，存到 node_templates/"""

    def execute(ctx: ActionContext) -> bool:
        node_name = ctx.node_name
        if not node_name:
            return False

        from ui.core.dock.floating_panel import themed_input_dialog
        from ui.core.i18n import t
        from ui.core.packager import Packager
        from ui.core.utils.dialog_utils import themed_message

        if not hasattr(main_window, "nodes_data") or node_name not in main_window.nodes_data:
            themed_message(main_window, t("k_title_error"), f"Node '{node_name}' not found", "error")
            return False

        node_info = main_window.nodes_data[node_name]
        node_path = node_info.get("path", "")

        if not node_path or not Path(node_path).is_dir():
            themed_message(main_window, t("k_title_error"), "Node directory not found", "error")
            return False

        desc = themed_input_dialog(main_window, t("k_save_as_template"), t("k_input_preset_description"), "")
        if desc is None:
            return False

        preset_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / "node_templates"
        preset_dir.mkdir(parents=True, exist_ok=True)

        base_name = Path(node_path).resolve().name
        bnos_path = preset_dir / base_name

        result = Packager.compress_directory(node_path, str(bnos_path), Packager.BNOS_EXTENSION)

        if not result:
            themed_message(main_window, t("k_title_error"), "Failed to pack preset node", "error")
            return False

        desc_json = {
            "name": base_name,
            "description": desc,
            "saved_at": datetime.now().isoformat(),
            "source_project": Path(getattr(main_window, "current_project_path", "") or "").name,
        }
        desc_path = preset_dir / (base_name + ".json")
        with desc_path.open("w", encoding="utf-8") as f:
            json.dump(desc_json, f, indent=2, ensure_ascii=False)

        themed_message(main_window, t("k_title_success"), t("_k_preset_saved").format(name=base_name), "info")
        return True

    ActionRegistry.register(
        ActionDefinition(
            id="node.save_as_template",
            name_i18n="k_save_as_template",
            category=ActionCategory.NODE,
            execute_fn=execute,
            requires_node=True,
        )
    )


def _register_open_preset_library(main_window):
    """注册"打开预设节点库"功能"""

    def execute(ctx: ActionContext) -> bool:
        main_window.show_template_selector()
        return True

    ActionRegistry.register(
        ActionDefinition(
            id="node.apply_template", name_i18n="k_select_template", category=ActionCategory.NODE, execute_fn=execute
        )
    )

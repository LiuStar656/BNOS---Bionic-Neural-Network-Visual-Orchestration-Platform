"""预设节点库 — save_as_preset / open_preset_library"""
import os
import json
from datetime import datetime

from ..action_definition import ActionDefinition, ActionCategory, ActionContext
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

        from ui.core.i18n import t
        from ui.core.floating_panel import themed_input_dialog
        from ui.core.utils.dialog_utils import themed_message
        from ui.core.packager import Packager

        if not hasattr(main_window, "nodes_data") or node_name not in main_window.nodes_data:
            themed_message(main_window, t("k_title_error"),
                           f"Node '{node_name}' not found", "error")
            return False

        node_info = main_window.nodes_data[node_name]
        node_path = node_info.get("path", "")

        if not node_path or not os.path.isdir(node_path):
            themed_message(main_window, t("k_title_error"),
                           "Node directory not found", "error")
            return False

        desc = themed_input_dialog(main_window, t("k_save_as_template"),
                                   t("k_input_preset_description"), "")
        if desc is None:
            return False

        preset_dir = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))))), "node_templates")
        os.makedirs(preset_dir, exist_ok=True)

        base_name = os.path.basename(os.path.normpath(node_path))
        bnos_path = os.path.join(preset_dir, base_name)

        result = Packager.compress_directory(node_path, bnos_path, Packager.BNOS_EXTENSION)

        if not result:
            themed_message(main_window, t("k_title_error"),
                           "Failed to pack preset node", "error")
            return False

        desc_json = {
            "name": base_name,
            "description": desc,
            "saved_at": datetime.now().isoformat(),
            "source_project": os.path.basename(getattr(main_window, "current_project_path", "") or ""),
        }
        desc_path = os.path.join(preset_dir, base_name + ".json")
        with open(desc_path, "w", encoding="utf-8") as f:
            json.dump(desc_json, f, indent=2, ensure_ascii=False)

        themed_message(main_window, t("k_title_success"),
                       t("_k_preset_saved").format(name=base_name), "info")
        return True

    ActionRegistry.register(ActionDefinition(
        id="node.save_as_template",
        name_i18n="k_save_as_template",
        category=ActionCategory.NODE,
        execute_fn=execute,
        requires_node=True
    ))


def _register_open_preset_library(main_window):
    """注册"打开预设节点库"功能"""
    def execute(ctx: ActionContext) -> bool:
        main_window.show_template_selector()
        return True

    ActionRegistry.register(ActionDefinition(
        id="node.apply_template",
        name_i18n="k_select_template",
        category=ActionCategory.NODE,
        execute_fn=execute
    ))

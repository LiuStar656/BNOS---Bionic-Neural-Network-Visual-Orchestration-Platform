"""
集中翻译 Key 注册表 (Translation Key Registry)
───────────────────────────────────────────
数据源: strings_cn.json / strings_en.json
生成方式: python -m ui.core.i18n.translation_keys --regenerate

用法:
    from ui.core.i18n.translation_keys import TK
    t(TK.PROJECT)           # 代替 t("k_project")
    t(TK._ABOUT_TEXT)       # 代替 t("_k_about_text")

验证:
    TK.validate()           # 检查所有 key 是否存在于 JSON 文件中
    TK.list_unused(glob)    # 扫描代码中未使用的 key
"""

from __future__ import annotations

import json
import os
import sys

from ui.core.logger import logger


def _load_json_keys() -> dict:
    """从 strings_cn.json 加载所有 key"""
    _here = os.path.dirname(os.path.abspath(__file__))
    _path = os.path.join(_here, "strings_cn.json")
    with open(_path, encoding="utf-8") as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════
# 从 JSON 动态加载验证集 — 确保生成的 key 与 JSON 一致
# ═══════════════════════════════════════════════════════════════════
_json_keys: dict = {}
try:
    _json_keys = _load_json_keys()
    logger.debug("TranslationKeys loaded %d keys from strings_cn.json", len(_json_keys))
except Exception as e:
    logger.warning("TranslationKeys: cannot load strings_cn.json (%s), validation disabled", e)


class TranslationKeys:
    """集中翻译 Key 注册表。

    所有 key 均以类属性形式暴露，IDE 可获得自动补全和重构支持。
    属性名规则: JSON key "k_project_new" → 属性 "PROJECT_NEW" (去掉 k_ 前缀，大写)
                       "_k_about_text"  → 属性 "_ABOUT_TEXT" (去掉 k 前缀，大写)

    提供方法:
        validate()          - 验证所有定义的 key 都存在于 JSON
        list_unused(glob)   - 扫描代码目录查找未使用的 key
        all_keys()          - 返回所有 key 列表
        count()             - 返回 key 总数
    """

    # ───── 项目 (Project) ─────
    PROJECT = "k_project"
    PROJECT_NEW = "k_project_new"
    PROJECT_OPEN = "k_project_open"
    IMPORT_EXPORT = "k_import_export"
    IMPORT_NODE = "k_import_node"
    IMPORT_NODE_DESC = "k_import_node_desc"
    IMPORT_PROJECT = "k_import_project"
    IMPORT_PROJECT_DESC = "k_import_project_desc"
    EXPORT_NODE = "k_export_node"
    EXPORT_NODE_DESC = "k_export_node_desc"
    EXPORT_PROJECT = "k_export_project"
    EXPORT_PROJECT_DESC = "k_export_project_desc"
    SELECT_TARGET_DIR = "k_select_target_dir"
    PROJECT_CREATED = "k_project_created"
    PROJECT_SELECT_DIR = "k_project_select_dir"
    PROJECT_OPEN_DIR = "k_project_open_dir"
    PROJECT_CREATE_NODES_DIR = "k_project_create_nodes_dir"
    PROJECT_NO_NODES_DIR = "k_project_no_nodes_dir"
    PROJECT_NO_PROJECT = "k_project_no_project"
    PROJECT_NODES_NOT_EXIST = "k_project_nodes_not_exist"
    PROJECT_SELECT_PARENT_DIR = "k_project_select_parent_dir"
    PROJECT_INPUT_NAME = "k_project_input_name"

    # ───── 节点 (Node) ─────
    NODE_CREATE = "k_node_create"
    NODE_CREATING = "k_node_creating"
    NODE_INIT = "k_node_init"
    NODE_START = "k_node_start"
    NODE_STOP = "k_node_stop"
    NODE_STARTING = "k_node_starting"
    NODE_STOPPING = "k_node_stopping"
    NODE_CONFIG = "k_node_config"
    NODE_EXPAND = "k_node_expand"
    NODE_DELETE = "k_node_delete"
    NODE_RENAME = "k_node_rename"
    NODE_LIST = "k_node_list"
    NODE_REFRESH = "k_node_refresh"
    NODE_REFRESH_LIST = "k_node_refresh_list"
    NODE_REFRESHING = "k_node_refreshing"
    NODE_SELECT_EXTERNAL = "k_node_select_external"
    NODE_MOUNT = "k_node_mount"
    NODE_UNMOUNT = "k_node_unmount"
    NODE_STYLE = "k_node_style"
    NODE_COLOR = "k_node_color"
    NODE_BG_COLOR = "k_node_bg_color"
    NODE_BORDER_COLOR = "k_node_border_color"
    NODE_TEXT_COLOR = "k_node_text_color"
    NODE_NO_PROJECT = "k_node_no_project"
    NODE_RIGHT_CLICK = "k_node_right_click"
    NODE_MOUNT_HELP = "k_node_mount_help"
    NODE_CREATE_DESC = "k_node_create_desc"
    NODE_CREATION_CANCELLED = "k_node_creation_cancelled"
    NODE_SELECT_FIRST = "k_node_select_first"
    NODE_ALREADY_RUNNING = "k_node_already_running"
    NODE_NOT_RUNNING = "k_node_not_running"
    NODE_NO_LOG = "k_node_no_log"
    NODE_NO_LOG_AVAILABLE = "k_node_no_log_available"
    NODE_NAME_INVALID = "k_node_name_invalid"
    NODE_INPUT_NEW_NAME = "k_node_input_new_name"
    NODE_INPUT_NEW_GROUP_NAME = "k_node_input_new_group_name"
    NODE_NO_UNGROUPED = "k_node_no_ungrouped"
    NODE_INFO = "k_node_info"
    NODE_CONTROL = "k_node_control"
    QUICK_ACTIONS = "k_quick_actions"
    OPEN_DIR = "k_open_dir"
    OPEN_TERMINAL = "k_open_terminal"
    OPEN_VSCODE = "k_open_vscode"
    NODE_NAME = "k_node_name"
    NODE_RESOURCES = "k_node_resources"
    NODE_STYLE_DETAILED = "k_node_style_detailed"
    NODE_STYLE_SQUARE = "k_node_style_square"
    NODE_STYLE_CIRCULAR = "k_node_style_circular"
    NODE_SELECT_START = "k_node_select_start"
    NODE_SELECT_STOP = "k_node_select_stop"
    NODE_SELECT_DELETE = "k_node_select_delete"
    NODE_SELECT_ADD = "k_node_select_add"
    NODE_SELECT_OPEN = "k_node_select_open"
    NODE_SELECT_VIEW_LOG = "k_node_select_view_log"
    NODE_SELECT_EDIT_CONFIG = "k_node_select_edit_config"
    NODE_SELECT_REMOVE = "k_node_select_remove"
    NODE_SELECT_MOVE = "k_node_select_move"
    NODE_SELECT_ONE = "k_node_select_one"
    NODE_ENTER_NAME = "k_node_enter_name"
    NODE_LANG_UNSUPPORTED = "k_node_lang_unsupported"
    NODE_MONITOR = "k_node_monitor"
    NODE_MONITOR_DOCK = "k_node_monitor_dock"
    NODE_MONITOR_DOCK_DESC = "k_node_monitor_dock_desc"
    NODE_LIST_FLOATING = "k_node_list_floating"
    NODE_LIST_DOCK = "k_node_list_dock"

    # ───── 组 (Group) ─────
    GROUP_CREATE = "k_group_create"
    GROUP_CREATE_GROUP = "k_group_create_group"
    GROUP_CREATE_NEW = "k_group_create_new"
    GROUP_RENAME = "k_group_rename"
    GROUP_DELETE = "k_group_delete"
    GROUP_MOVE = "k_group_move"
    GROUP_NO_AVAILABLE = "k_group_no_available"
    GROUP_UNGROUPED = "k_group_ungrouped"
    GROUP_NEW_AND_MOVE = "k_group_new_and_move"
    GROUP_EXPAND_COLLAPSE = "k_group_expand_collapse"
    GROUP_INPUT_NEW_NAME = "k_group_input_new_name"
    GROUP_LOCK_NO_MOVE = "k_group_lock_no_move"
    GROUP_LOCK_NO_MOVE_OUT = "k_group_lock_no_move_out"
    GROUP_LOCK_NO_MOVE_IN = "k_group_lock_no_move_in"
    GROUP_LOCK_NO_CROSS_ROOT = "k_group_lock_no_cross_root"
    GROUP_LOCK_NO_RENAME = "k_group_lock_no_rename"
    GROUP_LOCK_NO_DELETE = "k_group_lock_no_delete"
    GROUP_EXT_NO_DELETE = "k_group_ext_no_delete"
    GROUP_NODE_NOT_IN_GROUP = "k_group_node_not_in_group"
    GROUP_CONFIG_LOAD_FAIL = "k_group_config_load_fail"
    GROUP_CONFIG_SAVE_FAIL = "k_group_config_save_fail"
    GROUP_CLEARED_ALL = "k_group_cleared_all"

    # ───── 选择 (Selection) ─────
    SELECT_ALL = "k_select_all"
    SELECT_CLEAR = "k_select_clear"
    SELECT_CANCEL = "k_select_cancel"

    # ───── 画布 (Canvas) ─────
    CANVAS_START_CONNECTION = "k_canvas_start_connection"
    CANVAS_CLEAR_CONNECTIONS = "k_canvas_clear_connections"
    CANVAS_CLEAR_CONNECTIONS_DESC = "k_canvas_clear_connections_desc"
    CANVAS_CLEAR_CONFIG = "k_canvas_clear_config"
    CANVAS_DELETE_EDGE = "k_canvas_delete_edge"
    CANVAS_CHANGE_EDGE_COLOR = "k_canvas_change_edge_color"
    CANVAS_RESET_VIEW = "k_canvas_reset_view"
    CANVAS_EDGE_SNAP_ON = "k_canvas_edge_snap_on"
    CANVAS_EDGE_SNAP_OFF = "k_canvas_edge_snap_off"
    CANVAS_SHOW_DRAW_TOOLBAR = "k_canvas_show_draw_toolbar"
    CANVAS_HIDE_DRAW_TOOLBAR = "k_canvas_hide_draw_toolbar"
    CANVAS_COLOR = "k_canvas_color"
    CANVAS_BG_COLOR = "k_canvas_bg_color"
    CANVAS_GRID_COLOR = "k_canvas_grid_color"
    CANVAS_EDGE_COLOR = "k_canvas_edge_color"
    CANVAS_REMOVE_FROM = "k_canvas_remove_from"
    CANVAS_NEW_NODE = "k_canvas_new_node"
    CANVAS_CLEARED = "k_canvas_cleared"
    CANVAS_NODE_EXISTS = "k_canvas_node_exists"
    CANVAS_EDGE_EXISTS = "k_canvas_edge_exists"
    CANVAS_MONITOR = "k_canvas_monitor"
    CANVAS_ADD_TO = "k_canvas_add_to"
    CANVAS_OPEN_TERMINAL = "k_canvas_open_terminal"
    CANVAS_OPEN_TERMINAL_POWERSHELL = "k_canvas_open_terminal_powershell"
    CANVAS_OPEN_TERMINAL_CMD = "k_canvas_open_terminal_cmd"
    CANVAS_OPEN_TERMINAL_DEFAULT = "k_canvas_open_terminal_default"
    CANVAS = "k_canvas"
    CANVAS_EMPTY_HINT = "k_canvas_empty_hint"

    # ───── 配置 (Config) ─────
    CONFIG_EDIT = "k_config_edit"
    CONFIG_REFRESH = "k_config_refresh"
    CONFIG_SAVE = "k_config_save"
    CONFIG_SAVED = "k_config_saved"
    CONFIG_SAVE_SUCCESS = "k_config_save_success"
    CONFIG_SAVE_UNFORMATTED = "k_config_save_unformatted"
    EDIT_CONFIG = "k_edit_config"

    # ───── 日志 (Log) ─────
    LOG_VIEWER = "k_log_viewer"
    LOG_FILE_LABEL = "k_log_file_label"
    LOG_REFRESH = "k_log_refresh"
    LOG_CLEAR = "k_log_clear"
    LOG_CLEARED = "k_log_cleared"
    LOG_EMPTY = "k_log_empty"
    LOG_NO_FILE = "k_log_no_file"
    LOG_REFRESH_SUCCESS = "k_log_refresh_success"
    LOG_NO_CLEAR = "k_log_no_clear"
    VIEW_LOG = "k_view_log"
    LOG_LOAD_NODE = "k_log_load_node"
    LOG_CLOSE_START = "k_log_close_start"
    LOG_CLOSE_THREAD_WAIT = "k_log_close_thread_wait"
    LOG_CLOSE_THREAD_TIMEOUT = "k_log_close_thread_timeout"
    LOG_CLOSE_CANCELLED = "k_log_close_cancelled"
    LOG_CLOSE_DONE = "k_log_close_done"
    LOG_STATE_SAVED = "k_log_state_saved"
    LOG_STATE_RESTORED = "k_log_state_restored"
    LOG_CANVAS_CLEARED = "k_log_canvas_cleared"
    LOG_VIEW_RESET = "k_log_view_reset"
    LOG_VIEW_RESTORED = "k_log_view_restored"
    LOG_NODE_MOUNTED = "k_log_node_mounted"
    LOG_NODE_MOUNT_TOTAL = "k_log_node_mount_total"
    LOG_NODE_REGISTRY_SYNCED = "k_log_node_registry_synced"
    LOG_NODE_REGISTRY_FAIL = "k_log_node_registry_fail"
    LOG_NODE_RESTORED = "k_log_node_restored"

    # ───── 历史 (Edit/History) ─────
    EDIT_UNDO = "k_edit_undo"
    EDIT_REDO = "k_edit_redo"
    EDIT_CAN_UNDO = "k_edit_can_undo"
    EDIT_CANNOT_UNDO = "k_edit_cannot_undo"
    EDIT_CLEAR_HISTORY = "k_edit_clear_history"
    VIEW_HISTORY_PANEL = "k_view_history_panel"

    # ───── 终端 (Terminal) ─────
    TERMINAL_DOCK_TITLE = "k_terminal_dock_title"
    TERMINAL_NEW = "k_terminal_new"
    TERMINAL_TYPE_POWERSHELL = "k_terminal_type_powershell"
    TERMINAL_TYPE_CMD = "k_terminal_type_cmd"
    TERMINAL_TYPE_BASH = "k_terminal_type_bash"
    TERMINAL_INPUT_HINT = "k_terminal_input_hint"
    VIEW_TOGGLE_TERMINAL = "k_view_toggle_terminal"
    MENU_TOGGLE_TERMINAL = "k_menu_toggle_terminal"

    # ───── 菜单 (Menu) ─────
    MENU_FILE = "k_menu_file"
    MENU_EDIT = "k_menu_edit"
    MENU_TOOLS = "k_menu_tools"
    MENU_HELP = "k_menu_help"
    MENU_ABOUT = "k_menu_about"
    MENU_EXIT = "k_menu_exit"
    MENU_EXIT_DESC = "k_menu_exit_desc"
    MENU_TOGGLE_NODES = "k_menu_toggle_nodes"
    MENU_MONITOR = "k_menu_monitor"
    MENU_ABOUT_DESC = "k_menu_about_desc"
    MENU_CHANGELOG = "k_menu_changelog"
    MENU_CHANGELOG_DESC = "k_menu_changelog_desc"
    MENU_OPEN_PROJECT_DESC = "k_menu_open_project_desc"
    MENU_RESTART = "k_menu_restart"
    MENU_RESTART_DESC = "k_menu_restart_desc"

    # ───── 标题 / 对话框 (Title/Dialog) ─────
    TITLE_CONFIRM = "k_title_confirm"
    TITLE_WARNING = "k_title_warning"
    TITLE_ERROR = "k_title_error"
    TITLE_SUCCESS = "k_title_success"
    TITLE_INFO = "k_title_info"
    TITLE_ABOUT = "k_title_about"
    TITLE_CONFIRM_DELETE = "k_title_confirm_delete"
    TITLE_CONFIRM_CLEAR = "k_title_confirm_clear"
    TITLE_CONFIRM_UNMOUNT = "k_title_confirm_unmount"
    TITLE_CONFIRM_BATCH_DELETE = "k_title_confirm_batch_delete"
    TITLE_CONFIRM_REMOVE_CANVAS = "k_title_confirm_remove_canvas"
    TITLE_BATCH_START_RESULT = "k_title_batch_start_result"
    TITLE_BATCH_STOP_RESULT = "k_title_batch_stop_result"
    TITLE_BATCH_DELETE_RESULT = "k_title_batch_delete_result"
    TITLE_CLEAR_COMPLETE = "k_title_clear_complete"
    TITLE_ADD_TO_GROUP = "k_title_add_to_group"
    TITLE_JSON_ERROR = "k_title_json_error"
    TITLE_VSCODE_NOT_FOUND = "k_title_vscode_not_found"
    TITLE_WORKSPACE_CREATED = "k_title_workspace_created"
    TITLE_CONFIG_VIEWER = "k_title_config_viewer"
    TITLE_DETECT_RUNNING = "k_title_detect_running"

    # ───── 颜色设置 (Color) ─────
    COLOR_SETTINGS = "k_color_settings"
    COLOR_SETTINGS_DESC = "k_color_settings_desc"
    COLOR_CANVAS_BG = "k_color_canvas_bg"
    COLOR_NODE_STYLE = "k_color_node_style"
    COLOR_ANCHOR_STYLE = "k_color_anchor_style"
    COLOR_EDGE_STYLE = "k_color_edge_style"
    COLOR_TOAST_STYLE = "k_color_toast_style"
    COLOR_DOCK_STYLE = "k_color_dock_style"
    COLOR_QUICK_THEME = "k_color_quick_theme"
    COLOR_DARK_THEME = "k_color_dark_theme"
    COLOR_LIGHT_THEME = "k_color_light_theme"
    COLOR_APPLY = "k_color_apply"
    COLOR_RESET = "k_color_reset"
    COLOR_SELECT = "k_color_select"
    COLOR_SELECT_GROUP = "k_color_select_group"
    COLOR_APPLIED = "k_color_applied"
    COLOR_RESET_DONE = "k_color_reset_done"

    # ───── 属性面板 (Properties) ─────
    PROPERTIES = "k_properties"
    NO_SELECTION = "k_no_selection"
    CUSTOM_APPEARANCE = "k_custom_appearance"
    BASIC_CONFIG = "k_basic_config"
    FILTER_RULES = "k_filter_rules"
    ADD_RULE = "k_add_rule"
    DELETE_SELECTED = "k_delete_selected"
    CONNECTION_CONFIG = "k_connection_config"
    CONNECTION_DETAILS = "k_connection_details"
    UPSTREAM_NODE = "k_upstream_node"
    DOWNSTREAM_NODE = "k_downstream_node"
    UPSTREAM_PATH = "k_upstream_path"

    # ───── 字段标签 ─────
    FIELD_NODE_NAME = "k_field_node_name"
    FIELD_LISTEN_FILE = "k_field_listen_file"
    FIELD_OUTPUT_FILE = "k_field_output_file"
    FIELD_OUTPUT_TYPE = "k_field_output_type"
    FIELD_BG_COLOR = "k_field_bg_color"
    FIELD_GRID_COLOR = "k_field_grid_color"
    FIELD_GRID_OPACITY = "k_field_grid_opacity"
    FIELD_NODE_BG = "k_field_node_bg"
    FIELD_NODE_BORDER = "k_field_node_border"
    FIELD_NODE_TEXT = "k_field_node_text"
    FIELD_SELECTED_BORDER = "k_field_selected_border"
    FIELD_INPUT_ANCHOR = "k_field_input_anchor"
    FIELD_OUTPUT_ANCHOR = "k_field_output_anchor"
    FIELD_EDGE_COLOR = "k_field_edge_color"
    FIELD_EDGE_WIDTH = "k_field_edge_width"
    FIELD_TOAST_INFO = "k_field_toast_info"
    FIELD_TOAST_SUCCESS = "k_field_toast_success"
    FIELD_TOAST_WARNING = "k_field_toast_warning"
    FIELD_TOAST_ERROR = "k_field_toast_error"
    FIELD_TOAST_TEXT = "k_field_toast_text"
    FIELD_TOAST_OPACITY = "k_field_toast_opacity"
    FIELD_DOCK_ACTIVE = "k_field_dock_active"
    FIELD_DOCK_INACTIVE = "k_field_dock_inactive"

    # ───── 信息面板 (Info) ─────
    INFO_DETAILS = "k_info_details"
    INFO_ACTIONS = "k_info_actions"
    INFO_MONITOR = "k_info_monitor"
    INFO_MONITOR_HINT = "k_info_monitor_hint"
    INFO_CONFIG_SAVED = "k_info_config_saved"
    INFO_DETAILS_TITLE = "k_info_details_title"

    # ───── 资源/性能 (Resource/Performance) ─────
    SYS_RESOURCES = "k_sys_resources"
    RESOURCE_MONITOR = "k_resource_monitor"
    RESOURCE_MONITOR_DOCK = "k_resource_monitor_dock"
    RESOURCE_MONITOR_DESC = "k_resource_monitor_desc"
    PERFORMANCE = "k_performance"
    PERFORMANCE_PANEL = "k_performance_panel"
    SYSTEM = "k_system"
    NODES = "k_nodes"
    TRENDS = "k_trends"
    PROCESSES = "k_processes"
    DETAILS = "k_details"
    ALERTS = "k_alerts"
    ENABLE_ALERTS = "k_enable_alerts"
    NETWORK = "k_network"
    DISK = "k_disk"
    PEAK_CPU = "k_peak_cpu"
    METRIC = "k_metric"
    SELECT_NODE = "k_select_node"
    PID = "k_pid"
    CPU_CORES = "k_cpu_cores"
    CPU_USED = "k_cpu_used"
    MEMORY_USED = "k_memory_used"
    MEMORY_TOTAL = "k_memory_total"
    DISK_USED = "k_disk_used"
    DISK_TOTAL = "k_disk_total"
    NETWORK_IN = "k_network_in"
    NETWORK_OUT = "k_network_out"
    CPU = "k_cpu"
    MEMORY = "k_memory"
    STATUS = "k_status"
    STATUS_RUNNING = "k_status_running"
    STATUS_IDLE = "k_status_idle"
    STATUS_STOPPED = "k_status_stopped"
    STATUS_RUNNING_NODE = "k_status_running_node"
    STATUS_IDLE_TASK = "k_status_idle_task"
    STATUS_STOPPED_NODE = "k_status_stopped_node"
    STATUS_RUNNING_TASK = "k_status_running_task"
    STATUS_STOPPED_TASK = "k_status_stopped_task"
    STATUS_IDLE_TASK2 = "k_status_idle_task2"
    STATUS_SAVED = "k_status_saved"
    STATUS_SAVE_FAILED = "k_status_save_failed"
    STATUS_UPDATED = "k_status_updated"
    STATUS_REFRESHED = "k_status_refreshed"
    STATUS_RUNNING_APP = "k_status_running_app"
    STATUS_STOPPED_APP = "k_status_stopped_app"

    # ───── 通用 (General) ─────
    STOP = "k_stop"
    START = "k_start"
    ADD = "k_add"
    CLEAR_ALL = "k_clear_all"
    REFRESH = "k_refresh"
    VALUE = "k_value"
    PORT = "k_port"
    MODE = "k_mode"
    ACTION = "k_action"
    PATTERN = "k_pattern"
    TYPE = "k_type"
    DATE = "k_date"
    NAME = "k_name"
    IMPORT = "k_import"
    EXPORT = "k_export"
    IMPORT_TO_PROJECT = "k_import_to_project"
    SELECT_PRESET_FIRST = "k_select_preset_first"
    DELETE = "k_delete"
    SAVED_AT = "k_saved_at"
    SOURCE_PROJECT = "k_source_project"
    SIZE = "k_size"
    SAVE_AS_TEMPLATE = "k_save_as_template"
    INPUT_PRESET_DESCRIPTION = "k_input_preset_description"
    NO_DESCRIPTION = "k_no_description"

    # ───── 资源管理器 ─────
    EXPLORER = "k_explorer"
    SEARCH = "k_search"
    RUN = "k_run"
    EXTENSIONS = "k_extensions"
    HELP = "k_help"
    ACCOUNT = "k_account"
    MULTI_CANVAS = "k_multi_canvas"
    NEW = "k_new"
    NEW_CANVAS_TAB = "k_new_canvas_tab"
    NEW_CANVAS_TAB_DESC = "k_new_canvas_tab_desc"

    # ───── 预设节点库 (Preset) ─────
    PRESET_LIBRARY = "k_preset_library"
    SELECT_TEMPLATE = "k_select_template"
    PRESET_INFO = "k_preset_info"
    PRESET_DETAILS = "k_preset_details"

    # ───── 动作 (Actions) ─────
    ACTION_UNLOCK_EDIT = "k_action_unlock_edit"
    ACTION_LOCK_EDIT = "k_action_lock_edit"
    ACTION_REFRESH = "k_action_refresh"
    ACTION_CLEAR = "k_action_clear"
    ACTION_DIR = "k_action_dir"
    ACTION_CLOSE = "k_action_close"
    ACTION_EDIT = "k_action_edit"
    ACTION_LIVE = "k_action_live"

    # ───── 语言 (Language) ─────
    LANG_PYTHON = "k_lang_python"
    LANG_RUST = "k_lang_rust"
    LANG_NODEJS = "k_lang_nodejs"
    LANG_GO = "k_lang_go"
    LANG_JAVA = "k_lang_java"
    LANG_CPP = "k_lang_cpp"
    LANG_SHELL = "k_lang_shell"

    # ───── 错误信息 (Error) ─────
    ERR_NODE_FOLDER_MISSING = "k_err_node_folder_missing"
    ERR_OUTPUT_EMPTY = "k_err_output_empty"

    # ───── 通用按钮 ─────
    OK = "k_ok"
    CANCEL = "k_cancel"

    # ───── 样式 ─────
    STYLE_RECT = "k_style_rect"
    STYLE_LIGHT_RECT = "k_style_light_rect"

    # ───── 连线反推 ─────
    INFER_UPSTREAM_UNRESOLVED = "k_infer_upstream_unresolved"
    INFER_NO_UPSTREAM = "k_infer_no_upstream"
    INFER_DIAG_TITLE = "k_infer_diag_title"

    # ───── 确认/清空 ─────
    CONFIRM_CLEAR_CONNECTIONS = "k_confirm_clear_connections"

    # ═══════════════════════════════════════════════════════════════
    # 带 _k_ 前缀的 key (内部消息/动态消息/格式化字符串)
    # 属性名保留 _ 前缀以区分常规 key
    # ═══════════════════════════════════════════════════════════════

    # ───── 项目 ─────
    _PROJECT_EXISTS = "_k_project_exists"
    _PROJECT_CREATED = "_k_project_created"
    _PROJECT_OPENED = "_k_project_opened"
    _PROJECT_INVALID = "_k_project_invalid"
    _PROJECT_NAME = "_k_project_name"
    _RUNNING_DETECTED = "_k_running_detected"

    # ───── 节点 ─────
    _NODE_CANVAS_EXISTS = "_k_node_canvas_exists"
    _NODE_RUNNING = "_k_node_running"
    _NODE_STARTING = "_k_node_starting"
    _NODE_STARTED = "_k_node_started"
    _START_FAILED = "_k_start_failed"
    _START_FAIL = "_k_start_fail"
    _NODE_NOT_RUNNING_TOAST = "_k_node_not_running_toast"
    _NODE_STOPPING = "_k_node_stopping"
    _NODE_STOPPED = "_k_node_stopped"
    _STOP_FAIL = "_k_stop_fail"
    _NODE_EXITED = "_k_node_exited"
    _NODE_NOT_FOUND = "_k_node_not_found"
    _CONFIRM_DELETE_NODE = "_k_confirm_delete_node"
    _DELETE_NODE_CONFIRM = "_k_delete_node_confirm"
    _NODE_ON_CANVAS_WARNING = "_k_node_on_canvas_warning"
    _CONFIRM_BATCH_DELETE = "_k_confirm_batch_delete"
    _NODE_DELETED = "_k_node_deleted"
    _NODE_DELETE_FAILED = "_k_node_delete_failed"
    _NODE_NAME_EXISTS = "_k_node_name_exists"
    _FOLDER_EXISTS = "_k_folder_exists"
    _NODE_RENAMED = "_k_node_renamed"
    _RENAME_FAILED = "_k_rename_failed"
    _NO_CONFIG_JSON = "_k_no_config_json"
    _CONFIG_READ_FAIL = "_k_config_read_fail"
    _NODE_ALREADY_MOUNTED = "_k_node_already_mounted"
    _NODE_MOUNTED = "_k_node_mounted"
    _NODE_NOT_MOUNTED = "_k_node_not_mounted"
    _NODE_UNMOUNTED = "_k_node_unmounted"
    _CREATING_NODE = "_k_creating_node"
    _NODE_CREATE_SUCCESS = "_k_node_create_success"
    _NODE_CREATE_FAIL = "_k_node_create_fail"
    _NODE_CREATE_ERROR = "_k_node_create_error"
    _NO_LOG_YET = "_k_no_log_yet"
    _LOG_READ_FAIL = "_k_log_read_fail"
    _CLEAR_LOG_CONFIRM = "_k_clear_log_confirm"
    _CLEAR_FAILED = "_k_clear_failed"
    _NODE_FOLDER_MISSING_MSG = "_k_node_folder_missing_msg"
    _NODE_FOLDER_NOT_EXIST = "_k_node_folder_not_exist"
    _VENV_NOT_EXIST = "_k_venv_not_exist"
    _TERMINAL_OPEN_FAIL = "_k_terminal_open_fail"
    _JSON_INVALID_PROMPT = "_k_json_invalid_prompt"
    _CONFIG_SAVE_ERROR = "_k_config_save_error"
    _CLEAR_LOG_FILE_CONFIRM = "_k_clear_log_file_confirm"
    _LOG_FILE_CLEARED = "_k_log_file_cleared"
    _LOG_FILE_CLEAR_FAIL = "_k_log_file_clear_fail"
    _FOLDER_OPEN_FAIL = "_k_folder_open_fail"
    _NODE_INFO_LINE = "_k_node_info_line"
    _START_SCRIPT_MISSING = "_k_start_script_missing"
    _NODE_STARTED_PROP = "_k_node_started_prop"
    _NODE_START_FAIL_PROP = "_k_node_start_fail_prop"
    _NODE_STOPPED_PROP = "_k_node_stopped_prop"
    _NODE_STOP_FAIL_PROP = "_k_node_stop_fail_prop"
    _CONFIG_SAVE_FAIL = "_k_config_save_fail"
    _PROPERTY_HELP = "_k_property_help"
    _CONNECTED_TO = "_k_connected_to"
    _CANVAS_REMOVE_NODE_CONFIRM = "_k_canvas_remove_node_confirm"
    _NODE_EXPAND_CONFIRM_DELETE = "_k_node_expand_confirm_delete"

    # ───── 组 ─────
    _GROUP_REMOVE_FROM = "_k_group_remove_from"
    _ADD_TO_GROUP_PROMPT = "_k_add_to_group_prompt"
    _GROUP_CREATED = "_k_group_created"
    _NODE_MOVED_TO_GROUP = "_k_node_moved_to_group"
    _NODES_MOVED_TO_GROUP = "_k_nodes_moved_to_group"
    _NODE_REMOVED_FROM_GROUP = "_k_node_removed_from_group"
    _NODES_REMOVED_FROM_GROUP = "_k_nodes_removed_from_group"
    _GROUP_RENAMED = "_k_group_renamed"
    _CONFIRM_DELETE_GROUP = "_k_confirm_delete_group"
    _GROUP_DELETED = "_k_group_deleted"
    _GROUP_INFO = "_k_group_info"
    _GROUP_NODE_COUNT = "_k_group_node_count"
    _START_GROUP_NODES = "_k_start_group_nodes"
    _STOP_GROUP_NODES = "_k_stop_group_nodes"
    _UNGROUPED_NODES = "_k_ungrouped_nodes"
    _UNGROUPED_COUNT = "_k_ungrouped_count"
    _START_UNGROUPED = "_k_start_ungrouped"
    _STOP_UNGROUPED = "_k_stop_ungrouped"
    _CONFIRM_UNMOUNT = "_k_confirm_unmount"
    _NO_NODES_IN_GROUP = "_k_no_nodes_in_group"
    _STARTED_GROUP_NODES = "_k_started_group_nodes"
    _STOPPED_GROUP_NODES = "_k_stopped_group_nodes"
    _STARTED_UNGROUPED = "_k_started_ungrouped"
    _STOPPED_UNGROUPED = "_k_stopped_ungrouped"
    _AUTO_DELETED_GROUPS = "_k_auto_deleted_groups"
    _NODES_MOVED_TO_GROUP_BY_DRAG = "_k_nodes_moved_to_group_by_drag"
    _GROUP_CREATED_WITH_NODES = "_k_group_created_with_nodes"
    _MOUNT_LOCK_MOVE = "_k_mount_lock_move"
    _NODES_MOVED_TO_GROUP_BY_DRAG2 = "_k_nodes_moved_to_group_by_drag2"
    _NODES_REMOVED_FROM_GROUP_BY_DRAG = "_k_nodes_removed_from_group_by_drag"

    # ───── 选择/批量 ─────
    _SELECTED_COUNT = "_k_selected_count"
    _ADD_N_TO_CANVAS = "_k_add_n_to_canvas"
    _START_N_NODES = "_k_start_n_nodes"
    _STOP_N_NODES = "_k_stop_n_nodes"
    _OPEN_N_DIRS = "_k_open_n_dirs"
    _VIEW_N_LOGS = "_k_view_n_logs"
    _EDIT_N_CONFIGS = "_k_edit_n_configs"
    _DELETE_N_NODES = "_k_delete_n_nodes"
    _NODES_STOPPED = "_k_nodes_stopped"
    _FOLDERS_OPENED = "_k_folders_opened"
    _BATCH_EDIT_CONFIG = "_k_batch_edit_config"
    _BATCH_EDIT_CONFIG_PROMPT = "_k_batch_edit_config_prompt"
    _BATCH_START_RESULT = "_k_batch_start_result"
    _BATCH_STOP_RESULT = "_k_batch_stop_result"
    _BATCH_REMOVE_CONFIRM = "_k_batch_remove_confirm"
    _CONFIG_CLEARED = "_k_config_cleared"
    _BATCH_START_SELECTED = "_k_batch_start_selected"
    _BATCH_STOP_SELECTED = "_k_batch_stop_selected"
    _BATCH_REMOVE_SELECTED = "_k_batch_remove_selected"

    # ───── 关闭/退出 ─────
    _CLOSE_RUNNING_NODES = "_k_close_running_nodes"
    _NODES_CLOSED = "_k_nodes_closed"
    _NODES_BACKGROUND = "_k_nodes_background"
    _CANVAS_CRASHED = "_k_canvas_crashed"
    _START_NODE_TIP = "_k_start_node_tip"
    _STOP_NODE_TIP = "_k_stop_node_tip"

    # ───── 应用 ─────
    _APP_NAME = "_k_app_name"
    _ABOUT_TEXT = "_k_about_text"
    _CHANGELOG_NOT_FOUND = "_k_changelog_not_found"
    _CHANGELOG_READ_ERROR = "_k_changelog_read_error"

    # ───── 启动画面 (Splash) ─────
    _SPLASH_STARTING = "_k_splash_starting"
    _SPLASH_CONFIG = "_k_splash_config"
    _SPLASH_LOGGER = "_k_splash_logger"
    _SPLASH_MAIN_WIN = "_k_splash_main_win"
    _SPLASH_MAIN_READY = "_k_splash_main_ready"
    _SPLASH_PROJECT = "_k_splash_project"
    _SPLASH_DONE = "_k_splash_done"
    _SPLASH_SUBTITLE = "_k_splash_subtitle"
    _DELETE_SELECTED_GRAPHICS = "_k_delete_selected_graphics"

    # ───── 设置 (Settings) ─────
    _SETTINGS_TITLE = "_k_settings_title"
    _SETTINGS_LANGUAGE = "_k_settings_language"
    _SETTINGS_LANG_LABEL = "_k_settings_lang_label"
    _SETTINGS_SWITCH_LANG = "_k_settings_switch_lang"
    _LANG_CN = "_k_lang_cn"
    _LANG_EN = "_k_lang_en"
    _SETTINGS_PROCESS = "_k_settings_process"
    _SETTINGS_PROCESS_LABEL = "_k_settings_process_label"
    _SETTINGS_PROCESS_HINT = "_k_settings_process_hint"
    _SETTINGS_RESTART_TITLE = "_k_settings_restart_title"
    _SETTINGS_RESTART_MSG = "_k_settings_restart_msg"
    _SETTINGS_TAB_GENERAL = "_k_settings_tab_general"
    _SETTINGS_TAB_RENDERING = "_k_settings_tab_rendering"
    _SETTINGS_TAB_SHORTCUTS = "_k_settings_tab_shortcuts"
    _SETTINGS_RENDERING_CANVAS_SIZE = "_k_settings_rendering_canvas_size"
    _SETTINGS_RENDERING_PRESET = "_k_settings_rendering_preset"
    _SETTINGS_RENDERING_CUSTOM = "_k_settings_rendering_custom"
    _SETTINGS_RENDERING_WIDTH = "_k_settings_rendering_width"
    _SETTINGS_RENDERING_HEIGHT = "_k_settings_rendering_height"
    _SETTINGS_RENDERING_ANTIALIASING = "_k_settings_rendering_antialiasing"
    _SETTINGS_RENDERING_HINT = "_k_settings_rendering_hint"
    _SETTINGS_SHORTCUT_HINT = "_k_settings_shortcut_hint"
    _SETTINGS_SC_ACTION = "_k_settings_sc_action"
    _SETTINGS_SC_CURRENT = "_k_settings_sc_current"
    _SETTINGS_SC_DEFAULT = "_k_settings_sc_default"
    _SETTINGS_SC_RESET_ALL = "_k_settings_sc_reset_all"
    _SETTINGS_SC_RESET = "_k_settings_sc_reset"
    _SETTINGS_SC_EMPTY = "_k_settings_sc_empty"
    _SETTINGS_SC_CAPTURE = "_k_settings_sc_capture"
    _SETTINGS_SC_CAPTURE_INFO = "_k_settings_sc_capture_info"
    _SETTINGS_SC_DEFAULT_LABEL = "_k_settings_sc_default_label"

    # ───── 面板 ─────
    _PANEL = "_k_panel"

    # ───── 文件浏览器 ─────
    _FOLDER_PICKER_HEADER = "_k_folder_picker_header"
    _FOLDER_PICKER_PATH = "_k_folder_picker_path"
    _FILE_PICKER_HEADER = "_k_file_picker_header"
    _FILE_PICKER_PATH = "_k_file_picker_path"
    _FILE_NAME_HINT = "_k_file_name_hint"
    _BTN_UP = "_k_btn_up"
    _BTN_SELECT = "_k_btn_select"
    _BTN_SAVE = "_k_btn_save"
    _BTN_YES = "_k_btn_yes"
    _BTN_NO = "_k_btn_no"
    _FOLDER_CURRENT = "_k_folder_current"
    _BUTTON_CLOSE = "_k_button_close"
    _PREVIEW_TITLE = "_k_preview_title"
    _NO_PREVIEW = "_k_no_preview"
    _FILE_TOO_LARGE = "_k_file_too_large"
    _PREVIEW_ERROR = "_k_preview_error"

    # ───── 绘图 (Drawing) ─────
    _DRAW_RECT = "_k_draw_rect"
    _DRAW_ROUND_RECT = "_k_draw_round_rect"
    _DRAW_POLYGON = "_k_draw_polygon"
    _DRAW_ARROW = "_k_draw_arrow"
    _DRAW_TEXT = "_k_draw_text"
    _DRAW_STROKE = "_k_draw_stroke"
    _DRAW_FILL = "_k_draw_fill"
    _DRAW_LOCK = "_k_draw_lock"
    _DRAW_SHOW_HIDE = "_k_draw_show_hide"
    _DRAW_UNDO = "_k_draw_undo"
    _DRAW_REDO = "_k_draw_redo"
    _DRAW_DELETE_SEL = "_k_draw_delete_sel"
    _DRAW_CLEAR_ALL = "_k_draw_clear_all"
    _DRAW_TEXT_INPUT = "_k_draw_text_input"
    _DRAW_TEXT_TITLE = "_k_draw_text_title"
    _STYLE_ABSTRACT = "_k_style_abstract"
    _STYLE_DOT = "_k_style_dot"

    # ───── 颜色选择 ─────
    _SELECT_CANVAS_BG = "_k_select_canvas_bg"
    _SELECT_GRID_COLOR = "_k_select_grid_color"
    _SELECT_EDGE_COLOR = "_k_select_edge_color"
    _SELECT_NODE_BG = "_k_select_node_bg"
    _SELECT_NODE_BORDER = "_k_select_node_border"
    _SELECT_NODE_TEXT = "_k_select_node_text"

    # ───── VSCode 工作区 ─────
    _VSCODE_NOT_FOUND = "_k_vscode_not_found"
    _WORKSPACE_CREATED = "_k_workspace_created"
    _WORKSPACE_CREATED_NO_OPEN = "_k_workspace_created_no_open"
    _WORKSPACE_CREATED_NO_CODE = "_k_workspace_created_no_code"
    _VSCODE_WORKSPACE_CREATE_FAIL = "_k_vscode_workspace_create_fail"

    # ───── Trae IDE ─────
    _OPEN_TRAE = "_k_open_trae"
    _IDE_NOT_FOUND = "_k_ide_not_found"

    # ───── 预设节点 ─────
    _PRESET_SAVED = "_k_preset_saved"
    _PRESET_IMPORTED = "_k_preset_imported"

    # ───── 复合节点 (Composite) ─────
    COMPOSITE_COMPRESS = "k_composite_compress"
    COMPOSITE_DECOMPRESS = "k_composite_decompress"
    COMPOSITE_CANVAS_UNAVAILABLE = "k_composite_canvas_unavailable"
    COMPOSITE_NEED_2_NODES = "k_composite_need_2_nodes"
    _COMPOSITE_IS_ITSELF = "_k_composite_is_itself"
    _COMPOSITE_ALREADY_IN = "_k_composite_already_in"
    _COMPOSITE_NOT_ON_CANVAS = "_k_composite_not_on_canvas"
    _COMPOSITE_RUNNING = "_k_composite_running"
    COMPOSITE_UNKNOWN_LANGUAGE = "k_composite_unknown_language"
    COMPOSITE_LANGUAGE_MISMATCH = "k_composite_language_mismatch"
    COMPOSITE_CIRCULAR_DEPS = "k_composite_circular_deps"
    COMPOSITE_NOT_FOUND = "k_composite_not_found"
    COMPOSITE_INVALID_MODE = "k_composite_invalid_mode"
    COMPOSITE_RUNNING_CANNOT_SWITCH = "k_composite_running_cannot_switch"
    COMPOSITE_ALREADY_RUNNING = "k_composite_already_running"
    _COMPOSITE_COMPRESSED = "_k_composite_compressed"
    _COMPOSITE_DECOMPRESSED = "_k_composite_decompressed"
    _COMPOSITE_MODE_SET = "_k_composite_mode_set"
    _COMPOSITE_STARTED = "_k_composite_started"
    _COMPOSITE_STARTED_N = "_k_composite_started_n"
    COMPOSITE_STOPPED = "k_composite_stopped"
    _COMPOSITE_CRASH = "_k_composite_crash"
    _COMPOSITE_FINISHED = "_k_composite_finished"
    _START_SUBNODE_CONFLICT = "_k_start_subnode_conflict"
    _START_COMPOSITE_CONFLICT = "_k_start_composite_conflict"
    _COMPOSITE_WRITE_ORCH_FAILED = "_k_composite_write_orch_failed"
    _COMPOSITE_LOG_OPEN_FAILED = "_k_composite_log_open_failed"
    COMPOSITE_START_FAILED = "k_composite_start_failed"
    COMPOSITE_VENV_CREATE_FAILED = "k_composite_venv_create_failed"
    COMPOSITE_VENV_TIMEOUT = "k_composite_venv_timeout"
    COMPOSITE_VENV_ERROR = "k_composite_venv_error"
    COMPOSITE_DEPS_INSTALL_FAILED = "k_composite_deps_install_failed"
    COMPOSITE_DEPS_INSTALL_TIMEOUT = "k_composite_deps_install_timeout"
    COMPOSITE_DEPS_INSTALL_ERROR = "k_composite_deps_install_error"
    COMPOSITE_CONFIRM_TITLE = "k_composite_confirm_title"
    COMPOSITE_CONFIRM_TEXT = "k_composite_confirm_text"
    COMPOSITE_DECOMPRESS_CONFIRM_TITLE = "k_composite_decompress_confirm_title"
    COMPOSITE_DECOMPRESS_CONFIRM_TEXT = "k_composite_decompress_confirm_text"
    TRANSPORT_UNKNOWN = "k_transport_unknown"
    COMPOSITE_COMPRESS_FAILED = "k_composite_compress_failed"
    COMPOSITE_NAME_PROMPT = "k_composite_name_prompt"
    COMPOSITE_NAME_DIALOG_TITLE = "k_composite_name_dialog_title"
    _COMPOSITE_NO_ENTRY = "_k_composite_no_entry"
    _COMPOSITE_MULTI_ENTRY = "_k_composite_multi_entry"
    COMPOSITE_COLLAPSE_BLOCKED_TITLE = "k_composite_collapse_blocked_title"

    # Resource Limit
    RESOURCE_LIMITS = "k_resource_limits"
    RL_PRIORITY = "k_rl_priority"
    RL_PRIORITY_LOW = "k_rl_priority_low"
    RL_PRIORITY_BELOW_NORMAL = "k_rl_priority_below_normal"
    RL_PRIORITY_NORMAL = "k_rl_priority_normal"
    RL_PRIORITY_ABOVE_NORMAL = "k_rl_priority_above_normal"
    RL_PRIORITY_HIGH = "k_rl_priority_high"
    RL_CPU_LIMIT = "k_rl_cpu_limit"
    RL_MEMORY_LIMIT = "k_rl_memory_limit"
    RL_CPU_CORES = "k_rl_cpu_cores"
    RL_ALL_CORES = "k_rl_all_cores"
    RL_UNLIMITED = "k_rl_unlimited"
    RL_APPLY = "k_rl_apply"
    RL_APPLIED = "k_rl_applied"
    RL_CLEARED = "k_rl_cleared"
    RL_SAVE_FAILED = "k_rl_save_failed"
    RL_CPU_TOOLTIP = "k_rl_cpu_tooltip"
    RL_MEMORY_TOOLTIP = "k_rl_memory_tooltip"
    RL_AFFINITY_TOOLTIP = "k_rl_affinity_tooltip"

    # ═══════════════════════════════════════════════════════════════
    # 类方法 / 验证
    # ═══════════════════════════════════════════════════════════════

    @classmethod
    def all_keys(cls) -> list:
        """返回所有已定义的 key 值"""
        result = []
        for k, v in vars(cls).items():
            if k.startswith("__") or k.startswith("_"):
                continue
            if isinstance(v, str) and not callable(v) and v is not TranslationKeys:
                result.append(v)
        # 也包含 _k_ 前缀的 key
        for k, v in vars(cls).items():
            if not k.startswith("_") or k.startswith("__"):
                continue
            if isinstance(v, str) and v.startswith("_k_"):
                result.append(v)
        return result

    @classmethod
    def _all_key_pairs(cls) -> list:
        """返回所有 (attr_name, key_value) — 仅限翻译 key 属性"""
        result = []
        for k, v in vars(cls).items():
            if k.startswith("__"):
                continue
            if isinstance(v, str) and (v.startswith("k_") or v.startswith("_k_")):
                result.append((k, v))
        return result

    @classmethod
    def count(cls) -> int:
        """返回已定义的 key 总数"""
        return len(cls._all_key_pairs())

    @classmethod
    def validate(cls) -> dict:
        """验证所有定义的 key 是否在 JSON 中存在。

        返回: {"ok": True} 或 {"ok": False, "missing_in_json": [...], "extra_in_json": [...]}
        extra_in_json 仅作为信息提示，不影响 ok 状态。
        """
        if not _json_keys:
            return {"ok": False, "error": "Cannot load strings_cn.json"}

        defined_keys = set(cls.all_keys())
        json_key_set = set(_json_keys.keys())

        missing_in_json = defined_keys - json_key_set  # 定义了但 JSON 中不存在
        extra_in_json = json_key_set - defined_keys  # JSON 中存在但未定义 — 仅警告

        result = {"ok": True}
        if missing_in_json:
            result["ok"] = False
            result["missing_in_json"] = sorted(missing_in_json)
            logger.warning(
                "TranslationKeys validation: %d keys defined but missing in JSON: %s",
                len(missing_in_json),
                missing_in_json[:5],
            )
        if extra_in_json:
            result["extra_in_json"] = sorted(extra_in_json)
            logger.info(
                "TranslationKeys: %d keys in JSON not yet in TK registry: %s", len(extra_in_json), extra_in_json[:5]
            )
        return result

    @classmethod
    def list_unused(cls, source_dir: str = None) -> list:
        """扫描代码目录，找出 JSON 中存在但代码中未使用的 key。

        Args:
            source_dir: 扫描目录，默认项目根目录

        返回: 未使用 key 的列表
        """
        if not source_dir:
            source_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if not _json_keys:
            return []

        used = set()
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".venv", "venv", "node_modules")]
            for f in files:
                if f.endswith(".py"):
                    fpath = os.path.join(root, f)
                    try:
                        with open(fpath, encoding="utf-8", errors="ignore") as fh:
                            content = fh.read()
                    except Exception:
                        continue
                    for key in _json_keys:
                        if key in content:
                            used.add(key)

        return sorted(set(_json_keys.keys()) - used)


# ═══════════════════════════════════════════════════════════════════
# 模块级单例 — 便捷引用
# ═══════════════════════════════════════════════════════════════════
TK = TranslationKeys


# ═══════════════════════════════════════════════════════════════════
# 重新生成此文件 (python -m ui.core.i18n.translation_keys --regenerate)
# ═══════════════════════════════════════════════════════════════════
def _regenerate():
    """从 strings_cn.json 重新生成此文件。"""
    keys = sorted(_json_keys.keys())

    lines = []
    lines.append('"""')
    lines.append("集中翻译 Key 注册表 (Translation Key Registry)")
    lines.append("───────────────────────────────────────────")
    lines.append(f"数据源: strings_cn.json ({len(keys)} keys)")
    lines.append("生成方式: python -m ui.core.i18n.translation_keys --regenerate")
    lines.append("")
    lines.append("用法:")
    lines.append("    from ui.core.i18n.translation_keys import TK")
    lines.append('    t(TK.PROJECT)           # 代替 t("k_project")')
    lines.append('"""')
    lines.append("")
    # Write the rest similar to this file... (keep existing content)
    print(f"Regeneration would create file with {len(keys)} keys.")
    print("This is a stub - please manually update the file if needed.")


if __name__ == "__main__":
    if "--regenerate" in sys.argv:
        _regenerate()
    else:
        result = TK.validate()
        print(f"Keys defined: {TK.count()}")
        print(f"JSON keys: {len(_json_keys)}")
        print(f"Validation: {result}")

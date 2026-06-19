# 06_Translation Key Revision

**Date**: 2026-06-20

## Background

This session involved three separate translation issues:

1. **Debug panel missing k-values**: New panel code used `t("k_xxx")` but keys weren't in translation files
2. **Preset library refactoring**: Template system → preset library needed new translation keys and removal of old ones
3. **k-value mismatches**: Code key names didn't match translation file key names

## Changes

### 1. Fixed Code Key Mismatches

| # | File:Line | Wrong Key | Correct Key | Impact |
|---|-----------|-----------|-------------|--------|
| 1 | `_template.py:41` | `k_save_as_preset` | `k_save_as_template` | Save dialog title showed raw key |
| 2 | `builtin_view_actions.py:126` | `k_template_selector` | `k_select_template` | Menu item showed raw key |
| 3 | `builtin_view_actions.py:128` | `k_template` | `k_preset_library` | Menu hint showed raw key |
| 4 | `_template.py:21` | Wrong import path | `floating_panel.themed_input_dialog` | Template save raised ImportError |

### 2. New Translation Keys (12)

**Preset Library** (7):

| Key | Chinese | English |
|-----|---------|---------|
| `k_preset_library` | 预设节点库 | Preset Node Library |
| `k_preset_info` | 预设信息 | Preset Info |
| `k_preset_details` | 详情 | Details |
| `k_import_to_project` | 导入到当前项目 | Import to Current Project |
| `k_select_preset_first` | 请先选择一个预设 | Please select a preset first |
| `k_saved_at` | 保存时间 | Saved at |
| `k_source_project` | 来源项目 | Source Project |

**Save/Template** (2):

| Key | Chinese | English |
|-----|---------|---------|
| `k_save_as_template` | 保存为预设节点 | Save as Preset |
| `k_input_preset_description` | 请输入节点描述（可选） | Enter node description (optional) |

**Dynamic text** (2):

| Key | Chinese | English |
|-----|---------|---------|
| `_k_preset_saved` | 预设节点 "{name}" 已保存 | Preset "{name}" saved |
| `_k_preset_imported` | 预设节点 "{name}" 已导入 | Preset "{name}" imported |

**General** (1):

| Key | Chinese | English |
|-----|---------|---------|
| `k_delete` | 删除 | Delete |

### 3. Deleted Deprecated Keys (17)

Old template system keys, all references removed from code:

| Category | Deleted Keys |
|----------|-------------|
| Template core | `k_template`, `k_template_selector`, `k_template_info` |
| Categories | `k_category`, `k_all` |
| Import/Export | `k_import_template`, `k_export_template` |
| Parameters | `k_parameters`, `k_default` |
| Input | `k_input_template_name`, `k_select_category`, `k_input_category`, `k_template_description`, `k_input_description` |
| Messages | `_k_template_saved`, `_k_template_save_failed` |
| Other | `k_json_files` |

### 4. Debug Panel Completion (17)

See [02_Debug_Panel_Translation.md](./02_Debug_Panel_Translation.md).

## Translation File Final State

**`strings_cn.json`**: ~641 total keys
**`strings_en.json`**: ~631 total keys

## Impact

- **Modified**: `strings_cn.json`, `strings_en.json`, `builtin_view_actions.py`
- **New keys**: 29 (12 preset library + 17 debug panel)
- **Deleted keys**: 17 (template system legacy)
- **Fixed mismatches**: 3

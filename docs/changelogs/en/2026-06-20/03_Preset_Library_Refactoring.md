# 03_Preset Library Refactoring

**Date**: 2026-06-20

## Background

### Core Flaws of Old Template System

The old "Template Selector" had three irreconcilable problems:

1. **Incomplete save**: Only saved `config.json` field descriptions, not node program code (`main.py`). Templates were essentially parameter skeletons.

2. **Meaningless application**: Selecting a template called `node_creator_manager.create_node` which created a **skeleton node** — with venv, config.json, and startup scripts, but an **empty `main.py`**. Users had to rewrite all business code.

3. **Overlap with export**: The project already had complete `.bnos` node export/import (`ImportExportManager` + `Packager`), which packages full nodes (code + venv + config). Template system had minimal value and was functionally redundant.

### User Feedback

- "Each node's main program needs separate development"
- "I already have a complete node export function, isn't this template selector redundant?"

## Changes

### Architecture Decision: Deprecate Templates, Unify as Preset Node Library

Core concept: **Save = export complete node to `node_templates/`; Import = extract from `node_templates/` to project `nodes/`**. All operations reuse `Packager`'s `.bnos` compression/extraction mechanism.

### Deleted Files

| File | Reason |
|------|--------|
| `ui/dialogs/template_selector_dialog.py` | Old template selector, replaced by `PresetLibraryDialog` |
| `ui/core/node_template_manager.py` | Old template manager (~440 lines), CRUD replaced by Packager |

### New File

**[`ui/dialogs/preset_library_dialog.py`](file:///f:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/dialogs/preset_library_dialog.py)**

`PresetLibraryDialog(FloatingPanel)` — extends `FloatingPanel`, unified dark translucent borderless style.

**UI Layout**:
```
┌──────────────────────────────────────────┐
│  Title bar: Preset Node Library   [Refresh]│
├──────────────┬───────────────────────────┤
│  Presets     │  Preset Info               │
│              │  Name: data_processor       │
│  □  Reader    │  Description: Generic...   │
│  □  Processor │                             │
│  □  Visualizer│  Details                    │
│              │  Saved: 2026-06-20           │
│              │  Source: my_project          │
│              │  Size: 12.5 KB               │
├──────────────┴───────────────────────────┤
│          [Delete] [Cancel] [Import]        │
└──────────────────────────────────────────┘
```

**Key Methods**:

| Method | Function |
|--------|----------|
| `_load_presets()` | Scan `node_templates/`, read paired `.bnos` + `.json` |
| `_on_preset_selected(item)` | Select preset, show details |
| `_on_preset_double_clicked(item)` | Double-click to import |
| `_import_preset()` | Extract `.bnos` to `nodes/`, repair venv, refresh list |
| `_delete_preset()` | Remove `.bnos` + `.json` |

### Rewritten File

**[`ui/core/actions/node/_template.py`](file:///f:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/actions/node/_template.py)** (fully rewritten)

Registers two Actions:

**① `node.save_as_template` — Save as Preset Node**
```python
def execute(ctx: ActionContext) -> bool:
    node_path = main_window.nodes_data[node_name].get("path")
    desc = themed_input_dialog(main_window, t("k_save_as_template"),
                               t("k_input_preset_description"), "")
    Packager.compress_directory(node_path, bnos_path, ".bnos")
    # Generate node_templates/{name}.json description
```

**② `node.apply_template` — Open Preset Library**
```python
def execute(ctx: ActionContext) -> bool:
    dialog = PresetLibraryDialog(main_window)
    dialog.show()
```

### Modified Files

| File | Change |
|------|--------|
| `ui/main_window/panel.py` | `show_template_selector()` → `PresetLibraryDialog` import |
| `ui/core/application_context.py` | Removed `NodeTemplateManager` import/init/property |
| `ui/canvas/mixins/canvas_menus.py` | Registered `node.save_as_template` in right-click menu |
| `ui/core/actions/node/__init__.py` | Registered `_template` module |
| `ui/core/actions/builtin_view_actions.py` | Updated i18n key references |
| `ui/core/floating_panel.py` | Added `themed_input_dialog()` convenience function |
| `ui/core/import_export_manager.py` | Added `_repair_portable_venv()` function |

### New Helper Functions

**`_repair_portable_venv(node_dir)`** ([import_export_manager.py](file:///f:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/import_export_manager.py#L16-L75)):
- Rewrites `venv/pyvenv.cfg` `home` to current machine's Python directory
- Cleans `start.json` absolute `python_exe` and `path` fields

**`themed_input_dialog(parent, title, prompt, default)`** ([floating_panel.py](file:///f:/Bionic%20Neural%20Network%20Program%20Operating%20System/ui/core/floating_panel.py#L183-L186)): Delegates to `dialog_utils.themed_input`.

## Data Flow

```
Right-click node → ActionFactory → _template.py::save_as_preset
  ├── themed_input_dialog (user enters description)
  ├── Packager.compress_directory → node_templates/{name}.bnos
  └── json.dump → node_templates/{name}.json

Menu "Preset Library" → PresetLibraryDialog
  ├── _load_presets → scan node_templates/
  └── _import_preset
      ├── Packager.extract_package → temp dir
      ├── shutil.move → project nodes/{name}
      ├── _repair_portable_venv → repair portable venv
      └── main_window.refresh_nodes → refresh list
```

## Impact

- **New**: 1 file (`preset_library_dialog.py`)
- **Deleted**: 2 files
- **Modified**: 7 files
- **Backward compatible**: ✅ Right-click menu unchanged, `.bnos` format compatible

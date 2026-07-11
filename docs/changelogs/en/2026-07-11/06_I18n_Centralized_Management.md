# I18n Centralized Management

## Overview

Translation keys upgraded from scattered raw strings to a centralized registry. New `translation_keys.py` provides IDE autocomplete, consistency validation, and refactoring safety. Also filled in missing English rendering settings translations.

## Core Changes

### 1. Translation Key Registry

**Problem**: 434 `t("k_xxx")` calls across 46 files all used raw string literals — no autocomplete, prone to typos, unsafe to refactor, and impossible to validate consistency.

**Solution**: Created `ui/core/translation_keys.py`, mapping all 270+ translation keys from [strings_cn.json](file:///f:/Bionic Neural Network Program Operating System/ui/core/strings_cn.json) into Python class attributes. JSON files remain the single source of truth.

Modified / Added:

- **`ui/core/translation_keys.py`** (new):
  - `TranslationKeys` class: 270+ keys exposed as class attributes, grouped by feature module (Project, Node, Canvas, Group, Menu, Settings, etc.)
  - `TK = TranslationKeys` module-level convenience alias
  - `all_keys()` — returns all key values as a list
  - `count()` — returns total key count
  - `validate()` — checks TK-defined keys against JSON files for consistency
  - `list_unused(source_dir)` — scans source directory for JSON keys not referenced in code
  - Naming: `"k_project_new"` → `PROJECT_NEW`, `"_k_about_text"` → `_ABOUT_TEXT`

- **`ui/core/i18n.py`** (modified):
  - Added `validate_all_keys()` — one-time validation of TK registry against JSON at startup

### 2. Fill Missing English Rendering Translations

**Problem**: 8 translation keys under Settings → Rendering only existed in the Chinese JSON. Switching to English showed raw key names instead of translated text.

**Solution**: Completed [strings_en.json](file:///f:/Bionic Neural Network Program Operating System/ui/core/strings_en.json).

Added translations:

| Key | Translation |
|------|-------------|
| `_k_settings_tab_rendering` | Rendering |
| `_k_settings_rendering_canvas_size` | Canvas Resolution |
| `_k_settings_rendering_preset` | Preset: |
| `_k_settings_rendering_custom` | Custom |
| `_k_settings_rendering_width` | Width: |
| `_k_settings_rendering_height` | Height: |
| `_k_settings_rendering_antialiasing` | Enable Antialiasing |
| `_k_settings_rendering_hint` | Canvas resolution determines the maximum area... |

## Usage

```python
# Old (still compatible)
t("k_project_new")

# New (IDE autocomplete, refactoring-safe)
from ui.core.translation_keys import TK
t(TK.PROJECT_NEW)
```

## Tests

Added `tests/test_translation_keys.py` with 12 tests covering:
- Import and basic key assertions
- `all_keys()` includes both `k_` and `_k_` prefixes
- `validate()` consistency check
- No duplicate key values
- All JSON keys have corresponding TK attributes
- Backward compatibility (raw string `t()` still works)
- i18n integration test

## Affected Files

| File | Change Type |
|------|-------------|
| `ui/core/translation_keys.py` | Added — 270+ key centralized registry |
| `ui/core/i18n.py` | Modified — added `validate_all_keys()` |
| `ui/core/strings_en.json` | Modified — added 8 rendering translations |
| `tests/test_translation_keys.py` | Added — 12 tests |

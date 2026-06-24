# 04 Changelog Viewer

## Problem Overview

No in-app way to view changelogs; users had to manually browse the `docs/changelogs/` folder.

## Solution

Added a "View Changelog" menu item under "Help" that automatically reads the appropriate language changelog based on the current UI language.

## Implementation Details

### 1. ChangelogViewer Dialog Component

`ui/core/utils/changelog_viewer.py` — standalone changelog viewer dialog

- Self-drawn dark frameless dialog, black background with white text, consistent with project style
- Uses `get_lang()` to detect current language, auto-reads `docs/changelogs/{cn|en}/README.md`
- Uses `markdown` library (with `extra` extension) to convert Markdown + HTML to full HTML
- Uses `QWebEngineView` for rendering, fully supporting interactive `<details>` expand/collapse, link clicks, etc.

### 2. Menu & Action Registration

- Registered `view.changelog` Action in `builtin_view_actions.py`
- Added "View Changelog" menu item in Help menu (above "About", with separator) in `menu_manager.py`
- Added `show_changelog()` method in `main_window/interaction.py`

### 3. i18n Support

Added 4 translation keys:
- `k_menu_changelog` / `k_menu_changelog_desc` — menu text
- `_k_changelog_not_found` / `_k_changelog_read_error` — error messages

### 4. Dependency Update

Added `markdown>=3.5` to `requirements.txt` for Markdown-to-HTML conversion.

## Impact Scope

| Module | Impact |
|------|------|
| `ui/core/utils/changelog_viewer.py` | New, ~135 lines |
| `ui/menu/menu_manager.py` | Help menu new item |
| `ui/core/actions/builtin_view_actions.py` | Register `view.changelog` Action |
| `ui/main_window/interaction.py` | New `show_changelog()` |
| `ui/core/strings_cn.json` | 4 new i18n keys |
| `ui/core/strings_en.json` | 4 new i18n keys |
| `requirements.txt` | New `markdown>=3.5` |

## Verification

1. In Chinese mode, click "Help → View Changelog" — should show black-background dialog with Chinese changelogs
2. Switch to English and repeat — should show English changelogs
3. `<details>` blocks should be clickable to expand/collapse
4. Links should be clickable, opening in external browser

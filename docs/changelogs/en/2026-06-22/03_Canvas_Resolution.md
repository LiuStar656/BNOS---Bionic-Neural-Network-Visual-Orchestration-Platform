# 03_Canvas Resolution Settings

**Date**: 2026-06-22

## Background

Before this update, canvas size and antialiasing were hard-coded:

1. **Fixed scene rect**: The `NodeCanvas` initialized with a static `setSceneRect(-w, -h, 2w, 2h)`. Users with large node workflows often hit the boundary; users with small workflows wasted paint time over a huge empty region.
2. **No antialiasing toggle**: Antialiasing was forced on for every paint call, even on low-power machines where users preferred faster, aliased drawing.
3. **No UI for customization**: No dialog exposed canvas size or rendering quality options.

## Changes

### ui/dialogs/settings_dialog.py - New "Rendering" Tab

A new tab "settings.rendering.title" is added to the settings dialog. Layout:

```
+-- Rendering ------------------------------------+
|                                                   |
|  Canvas Resolution                                |
|  +----------+  +----------+  +----------+         |
|  |  1000    |  |  2000    |  |  5000    |  ...    |
|  +----------+  +----------+  +----------+         |
|                                                   |
|  Custom Size                                      |
|  Width  [ 5000 ] px    Height [ 5000 ] px         |
|                                                   |
|  [x] Antialiasing                                 |
|                                                   |
|  (!) Restart required after changes               |
|                                                   |
|         [ OK ]  [ Cancel ]                        |
+---------------------------------------------------+
```

Five preset buttons:

| Label | Width x Height |
|-------|----------------|
| `preset_1000` | 1000 x 1000 |
| `preset_2000` | 2000 x 2000 |
| `preset_5000` | 5000 x 5000 (Default) |
| `preset_8000` | 8000 x 8000 |
| `preset_10000` | 10000 x 10000 |

Input validation: values are clamped to **500 - 10000** px. The antialiasing checkbox defaults to **on**.

Clicking a preset populates the custom width/height inputs; editing the inputs un-selects the preset row so the user sees their custom value is active.

**OK button** saves the new config to `app_config.json` under the `rendering` key and shows a `restart_tip` toast: "Rendering settings applied. Restart BNOS for the change to take effect."

### ui/core/app_config.py - Default Config

The default config dictionary now includes a `rendering` object:

```json
{
  "rendering": {
    "canvas_width": 5000,
    "canvas_height": 5000,
    "antialiasing": true
  }
}
```

Load logic: `AppConfig.get("rendering")` returns this block; missing fields fall back to defaults.

### ui/canvas/canvas_view.py - NodeCanvas Initialization

On startup, `NodeCanvas` reads the rendering configuration:

```python
from ui.core.app_config import AppConfig

rendering = AppConfig.get("rendering", {})
canvas_width = int(rendering.get("canvas_width", 5000))
canvas_height = int(rendering.get("canvas_height", 5000))
antialiasing = bool(rendering.get("antialiasing", True))

self.setSceneRect(-canvas_width // 2, -canvas_height // 2,
                  canvas_width, canvas_height)

if antialiasing:
    self.setRenderHint(QPainter.Antialiasing, True)
    self.setRenderHint(QPainter.SmoothPixmapTransform, True)
else:
    self.setRenderHint(QPainter.Antialiasing, False)
    self.setRenderHint(QPainter.SmoothPixmapTransform, False)
```

The scene rect is centered at `(0, 0)` to keep the existing coordinate conventions.

### Translation Keys Added

Added to `ui/core/strings_cn.json` and `ui/core/strings_en.json`:

| Key | English | Usage |
|-----|---------|-------|
| `settings.rendering.title` | Rendering | Tab title |
| `preset_1000` | 1000 | Preset button |
| `preset_2000` | 2000 | Preset button |
| `preset_5000` | 5000 (Default) | Preset button |
| `preset_8000` | 8000 | Preset button |
| `preset_10000` | 10000 | Preset button |
| `custom` | Custom | Custom size header |
| `width` | Width | Width spinbox label |
| `height` | Height | Height spinbox label |
| `px` | px | Unit suffix |
| `antialiasing` | Antialiasing | Checkbox label |
| `restart_tip` | Rendering settings applied. Restart BNOS for the change to take effect. | Toast after OK |

### app_config.json Storage Example

```json
{
  "rendering": {
    "canvas_width": 8000,
    "canvas_height": 8000,
    "antialiasing": true
  }
}
```

### Settings Dialog Load / Save Flow

```
Open settings dialog
  +-- _load_from_config() -> reads AppConfig("rendering")
        +-- matches preset button OR selects "Custom"
        +-- fills width / height spinboxes (validated 500-10000)
        +-- sets antialiasing checkbox

User edits
  +-- clicking preset -> populates spinboxes
  +-- editing spinbox -> deselects preset row, shows Custom
  +-- toggling antialiasing checkbox

User clicks OK
  +-- _save_to_config() -> AppConfig.set("rendering", {...})
        +-- save_app_config() -> writes app_config.json
  +-- t("restart_tip") toast shown
```

### Design Highlights

| Feature | Implementation |
|---------|---------------|
| **Default values** | 5000 x 5000 canvas, antialiasing enabled |
| **Validation range** | 500 - 10000 px per dimension |
| **Preset -> custom coupling** | Clicking a preset overwrites spinboxes; manual edit marks as custom |
| **Antialiasing toggle** | Controls both `Antialiasing` and `SmoothPixmapTransform` together |
| **Restart prompt** | `restart_tip` toast after OK - settings only read once at NodeCanvas construction |
| **Backward-compatible config** | Missing `rendering` section falls back to defaults in `app_config.py` |

### Impact

- **Modified**: `ui/dialogs/settings_dialog.py` - new tab, preset buttons, custom inputs, antialiasing checkbox
- **Modified**: `ui/core/app_config.py` - default `rendering` block, get/set accessors
- **Modified**: `ui/canvas/canvas_view.py` - reads AppConfig("rendering") into scene rect and render hints
- **Modified**: `ui/core/strings_cn.json` and `ui/core/strings_en.json` - ~12 new translation keys
- **Runtime behavior**: settings are applied once at startup; changing them requires a restart (consistent with Qt scene rect / render hint lifecycle)
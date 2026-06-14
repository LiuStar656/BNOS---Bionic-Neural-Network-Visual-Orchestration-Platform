# Adaptive Node View (ComfyUI-Style Detailed Mode)

## 📋 Overview

This update completes **Phase 12: Adaptive Node View**. A third node style — "Detailed" — is introduced, rendering parameter editing controls directly on the canvas (similar to ComfyUI). Parameter changes are written back to `config.json` in real time with bidirectional data binding. All style switches are driven through a unified right-click menu, with exact node size restoration and no residual widgets.

---

## 🏗️ Architecture

```
                             config.json
                      { "parameters": [ ... ] }
                              │
                       ┌──────▼──────┐
                       │ NodeConfigParser │
                       │  Parse defs   │
                       └──────┬──────┘
                              │
                       ┌──────▼──────┐
                       │ ParameterWidgets │
                       │  Widget Factory  │
                       │  string/text/password  │
                       │  int/float/bool/enum  │
                       │  file/dir/color/range │
                       └──────┬──────┘
                              │
                 ┌────────────┼────────────┐
         ┌───────▼──────┐   ┌▼────────┐   ┌▼────────┐
         │ DetailedNodeStyle │   │ RectNodeStyle │   │ DotNodeStyle │
         │  Content-driven  │   │  Square    │   │  Circle   │
         │  size, status_sh │   │  140×80   │   │  80×80   │
         └────────┬───────┘   └──────────┘   └──────────┘
                  │
           ┌──────▼──────┐
           │  NodeItem    │
           │  _proxy_widgets │
           │  _param_widgets │
           │  set_style()   │
           └────────────────┘
```

---

## 🎯 Core Features

### 1. Parameter JSON Standard Format

**`node_python_1/config.json` Example**

```json
{
    "node_name": "cloud_inference",
    "listen_upper_file": "../data/upper_data.json",
    "output_file": "./output.json",
    "parameters": [
        {
            "name": "provider",
            "type": "enum",
            "label": "Cloud Provider",
            "default": "openai",
            "options": ["openai", "anthropic", "google"]
        },
        {
            "name": "model",
            "type": "enum",
            "label": "Model",
            "default": "gpt-4o",
            "options": ["gpt-4o", "gpt-4o-mini", "claude-sonnet"]
        },
        {
            "name": "temperature",
            "type": "float",
            "label": "Temperature",
            "default": 0.7,
            "min": 0.0,
            "max": 2.0,
            "step": 0.1
        },
        {
            "name": "api_key",
            "type": "password",
            "label": "API Key",
            "default": ""
        },
        {
            "name": "max_tokens",
            "type": "int",
            "label": "Max Tokens",
            "default": 2048,
            "min": 1,
            "max": 128000
        },
        {
            "name": "system_prompt",
            "type": "text",
            "label": "System Prompt",
            "default": "You are a helpful AI assistant",
            "rows": 3
        }
    ]
}
```

**Parameter Type → Widget Mapping**

| type | Widget | Qt Component | Features |
|------|--------|--------------|----------|
| `string` | Single-line text input | `QLineEdit` | Free-form text |
| `text` | Multi-line text input | `QPlainTextEdit` | Supports `rows` parameter |
| `password` | Password input | `QLineEdit(EchoMode.Password)` | Input masked |
| `int` | Integer input | `QSpinBox` | Supports `min/max/step` |
| `float` | Floating-point input | `QDoubleSpinBox` | Supports `min/max/step/decimals` |
| `bool` | Checkbox | `QCheckBox` | Toggle value |
| `enum` | Dropdown | `QComboBox` | Supports `options` |
| `file` | File picker | `QLineEdit` + file dialog | `file_filter` |
| `directory` | Directory picker | `QLineEdit` + directory dialog | |
| `color` | Color picker | `QPushButton` + `QColorDialog` | Live color preview |
| `range` | Slider + value | `QSlider` + `QLabel` | Supports `min/max` |

---

### 2. NodeConfigParser — Parameter Parser

**New file**: `ui/core/node_config_parser.py` (55 lines)

```python
@dataclass
class ParameterDef:
    name: str
    type: str
    label: str
    default: Any = None
    required: bool = False
    # Constraint fields
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    decimals: int = 2
    options: list[str] = field(default_factory=list)
    file_filter: str = ""
    rows: int = 1

class NodeConfigParser:
    @staticmethod
    def parse(config: dict) -> list[ParameterDef]:
        raw = config.get("parameters", [])
        return [ParameterDef(**p) for p in raw]

    @staticmethod
    def extract_values(config: dict) -> dict[str, Any]:
        result = {}
        for p in (config.get("parameters") or []):
            result[p["name"]] = config.get(p["name"], p.get("default"))
        return result

    @staticmethod
    def has_parameters(config: dict) -> bool:
        return bool(config and config.get("parameters"))
```

---

### 3. ParameterWidgets — Widget Factory

**New file**: `ui/canvas/parameter_widgets.py` (372 lines)

**Base class `ParameterWidget(QWidget)`**:

```python
class ParameterWidget(QWidget):
    value_changed = Signal(str, object)  # param_name, value
    def __init__(self, param: ParameterDef, current_value=None): ...
    def get_value(self): ...
    def set_value(self, v): ...
    @classmethod
    def create(cls, param: ParameterDef, current_value=None): ...
```

**11 Concrete Widget Classes**:

| Class | Function | Signal |
|-------|----------|--------|
| `StringWidget` | Label + single-line input | `textChanged` → `value_changed` |
| `TextWidget` | Label + multi-line input (height=rows×22) | `textChanged` → `value_changed` |
| `PasswordWidget` | Label + password input (masked) | `textChanged` → `value_changed` |
| `IntWidget` | Label + QSpinBox | `valueChanged` → `value_changed` |
| `FloatWidget` | Label + QDoubleSpinBox | `valueChanged` → `value_changed` |
| `BoolWidget` | Label + QCheckBox | `stateChanged` → `value_changed` |
| `EnumWidget` | Label + QComboBox | `currentTextChanged` → `value_changed` |
| `FilePickerWidget` | Label + QLineEdit + QPushButton(📁) | Emits on confirm |
| `DirPickerWidget` | Label + QLineEdit + QPushButton(📂) | Emits on confirm |
| `ColorWidget` | Label + QPushButton(color) + QColorDialog | Emits on selection |
| `RangeWidget` | Label + QSlider + QLabel(value) | `valueChanged` → `value_changed` |

**Size constraints**:
- Label width auto-calculated from text content (`QFontMetrics`)
- Each parameter row: `setMinimumHeight(24)`
- Input controls: `setMinimumHeight(22)`

---

### 4. DetailedNodeStyle — Detailed View Style

**Modified file**: `ui/canvas/items/node_style.py`

```python
class DetailedNodeStyle(RectNodeStyle):
    """Detailed node view — renders parameter controls directly on the canvas"""
    style_key = "detailed"
    style_name = "Detailed"
    is_dot = False
    status_show = True

    HEADER_HEIGHT = 26       # Title area
    DIVIDER_HEIGHT = 4       # Space between title and parameters
    BOTTOM_PADDING = 6       # Bottom margin
    ROW_HEIGHT = 24          # Single parameter row height
    MIN_NODE_WIDTH = 240     # Minimum width fallback

    def set_sizes(self, content_width: int, content_height: int):
        self._computed_width = max(self.MIN_NODE_WIDTH, content_width)
        self._computed_height = (
            self.HEADER_HEIGHT + self.DIVIDER_HEIGHT +
            content_height + self.BOTTOM_PADDING
        )
        self.node_width = self._computed_width
        self.node_height = self._computed_height

    def apply(self, node_item):
        if hasattr(node_item, "_status_widget") and node_item._status_widget:
            node_item._status_widget.set_visible(False)
        node_item._build_detailed_view()
```

**STYLES Registry Update**:

```python
STYLES = {
    "rect": DarkRectNodeStyle,     # Square
    "dot": DotNodeStyle,            # Circle
    "detailed": DetailedNodeStyle,  # Detailed (NEW)
}
```

---

### 5. NodeItem Extension — Widget Embedding & Data Binding

**Modified file**: `ui/canvas/items/node_item.py`

New data structures:

```python
self._proxy_widgets: list[QGraphicsProxyWidget] = []
self._param_widgets: dict[str, ParameterWidget] = {}
self._rect_default_width = 140   # Original node width
self._rect_default_height = 80   # Original node height
```

**Core method `_build_detailed_view()`**:

```python
def _build_detailed_view(self):
    # Load config.json
    config = self._get_node_config()
    if not config or not NodeConfigParser.has_parameters(config):
        # No parameters defined — fall back to plain square
        from ui.canvas.items.node_style import DarkRectNodeStyle
        fallback = DarkRectNodeStyle()
        fallback.node_width = self._rect_default_width
        fallback.node_height = self._rect_default_height
        self._style = fallback
        fallback.apply(self)
        return

    params = NodeConfigParser.parse(config)
    values = NodeConfigParser.extract_values(config)

    # Phase 1: Build all ParameterWidgets, get natural sizes via adjustSize()
    max_label_w = 0
    max_control_w = 200
    total_content_h = 0
    temp_widgets = []
    for param in params:
        current = values.get(param.name, param.default)
        widget = ParameterWidget.create(param, current)
        widget.adjustSize()
        temp_widgets.append(widget)
        total_content_h += max(widget.sizeHint().height(), ROW_HEIGHT)

    margin_left, margin_right = 10, 10
    content_w = max_label_w + max_control_w + 8
    content_h = total_content_h

    # Phase 2: Set node dimensions, draw the rect frame
    self._style.set_sizes(content_w, content_h)
    # Call RectNodeStyle.apply — skips build, does setRect + style rendering
    RectNodeStyle.apply(self._style, self)

    # Phase 3: Embed all ParameterWidgets into QGraphicsProxyWidget
    y_offset = HEADER_HEIGHT + DIVIDER_HEIGHT
    content_area_w = self._style.node_width - margin_left - margin_right
    for widget in temp_widgets:
        widget.setFixedWidth(content_area_w)
        proxy = QGraphicsProxyWidget(self)
        proxy.setWidget(widget)
        proxy.setPos(margin_left, y_offset)
        proxy.setZValue(5)
        self._proxy_widgets.append(proxy)
        self._param_widgets[widget.param.name] = widget
        y_offset += widget.height()

    # Phase 4: Listen for parameter changes
    for widget in self._param_widgets.values():
        widget.value_changed.connect(self._on_param_changed)
```

**Bidirectional Data Binding**:

```python
def _on_param_changed(self, name: str, value):
    """Parameter changed → immediately write back to config.json"""
    config = self._get_node_config()
    if config is not None:
        config[name] = value
        self._save_node_config(config)

def _get_node_config(self) -> Optional[dict]:
    pw = self._canvas_ref.parent_window
    if pw:
        data = pw.nodes_data.get(self._node_name, {})
        return data.get('config')
    return None

def _save_node_config(self, config: dict):
    """Save config and sync to disk"""
    # Update in-memory nodes_data + write to config.json file
```

---

### 6. Style Switching — Unified `set_style()` Entry Point

**Modified file**: `ui/canvas/items/node_item.py` (the `set_style` method)

```python
def set_style(self, style):
    # 1) Destroy old detailed widgets
    if hasattr(self, '_proxy_widgets') and self._proxy_widgets:
        self._destroy_detailed()

    self._style = style

    # 2) Set correct dimensions based on style type
    # (Prevents class default (140×120) from overriding
    #  the node's original 140×80 creation size)
    if isinstance(self._style, DotNodeStyle):
        self._style.node_width = 80
        self._style.node_height = 80
    elif isinstance(self._style, DetailedNodeStyle):
        pass  # Content-driven, calculated by _build_detailed_view()
    elif isinstance(self._style, RectNodeStyle):
        self._style.node_width = self._rect_default_width   # 140
        self._style.node_height = self._rect_default_height  # 80

    # 3) Apply the style
    self._style.apply(self)
    self._style.apply_status(self, self.status)

    # 4) Re-layout status bar with new dimensions
    if self._style.status_show and not self._style.is_dot:
        if not self._status_widget:
            self._status_widget = NodeStatusWidget(self)
        self._status_widget.set_visible(True)
        self._status_widget.update_layout()
        self._start_time = None
        self._connect_resource_monitor_signals()
    else:
        if self._status_widget:
            self._status_widget.set_visible(False)
            self._status_widget = None

    self._update_selection_ring(self.isSelected())
    if self.scene():
        self.scene().update()
```

**Modified file**: `ui/canvas/canvas_menus.py` (`_switch_node_style` simplified)

```python
def _switch_node_style(self, style_key, node_item):
    from ui.canvas.items.node_style import STYLES
    cls = STYLES.get(style_key)
    if not cls:
        return
    node_item.set_style(cls())  # All logic handled by NodeItem
```

---

### 7. NodeStatusWidget — Style Decoupling

**Modified file**: `ui/canvas/items/node_status_widget.py`

**Problem**: `__init__` cached `self._style = node_item._style`, which became stale after style changes.

**Fix**: Read the current `node_item._style` directly each time layout happens:

```python
def _layout_widgets(self):
    current_style = self.node_item._style
    w, h = current_style.node_width, current_style.node_height
    # ... position all controls using current dimensions

def update_status(self, cpu_percent, mem_mb, duration_seconds):
    current_style = self.node_item._style
    w, h = current_style.node_width, current_style.node_height
    # ... re-render progress bars using current dimensions
```

---

## 📂 File Changes Summary

| File | Action | Lines | Description |
|------|--------|-------|-------------|
| `ui/core/node_config_parser.py` | **New** | 55 | ParameterDef + NodeConfigParser |
| `ui/canvas/parameter_widgets.py` | **New** | 372 | 11 parameter widget types + factory |
| `ui/canvas/items/node_style.py` | Modified | +32 | DetailedNodeStyle class + STYLES registration |
| `ui/canvas/items/node_item.py` | Modified | +80 | _proxy_widgets/_param_widgets, _build_detailed_view, set_style refactor |
| `ui/canvas/canvas_menus.py` | Modified | -10 | _switch_node_style simplified to set_style() |
| `ui/canvas/items/node_status_widget.py` | Modified | +12 | No style reference caching, always reads node_item._style |
| `ui/core/strings_cn.json` | Modified | +3 | "Detailed" / "Square" / "Circle" i18n |
| `ui/core/strings_en.json` | Modified | +3 | "Detailed" / "Square" / "Circle" i18n |

---

## 🐛 Bug Fixes and Root Cause Analysis

### Issue 1: Node size incorrect after style switching

**Symptom**: After switching from detailed back to square mode, the node was 40px taller, with extra spacing in the status bar.

**Root cause**: Nodes were created with `h=80` (default in `__init__`), but the `NodeStyle` class default is `node_height=120`. When switching, a fresh `DarkRectNodeStyle()` instance used the class default 120, so the node grew from 140×80 to 140×120.

**Fix**:
1. Store `self._rect_default_width/height` in `NodeItem.__init__`
2. In `set_style()`, use `isinstance` to determine style type and apply correct dimensions:
   - RectNodeStyle → original (140, 80)
   - DotNodeStyle → class default (80, 80)
   - DetailedNodeStyle → content-driven

### Issue 2: Status bar still using old dimensions

**Symptom**: After switching, CPU/MEM progress bar positions didn't match new node dimensions.

**Root cause**: `NodeStatusWidget.__init__` cached `self._style = node_item._style`, which pointed to the old style object after switching.

**Fix**: Remove `self._style` cache in `_layout_widgets` and `update_status`, always read `self.node_item._style`. Call `update_layout()` after `set_style()`.

### Issue 3: QComboBox dropdown popup clipped

**Symptom**: In detailed mode, QComboBox dropdown lists were clipped by node boundaries.

**Root cause**: `QGraphicsProxyWidget`-embedded QComboBox has incorrect `mapToGlobal()` coordinate calculation.

**Fix**: `_ProxyAwareComboBox` overrides `showPopup()` — manually computes correct screen coordinates via `proxy → scene → view → viewport → global`.

### Issue 4: Proxy widgets remain visible after switch

**Symptom**: After switching back to square mode, old parameter controls were still visible.

**Root cause**: `_destroy_detailed()` didn't fully clean up via `scene.removeItem()` + `setWidget(None)`.

**Fix**: Always call `_destroy_detailed()` before switching styles, reset cache mode before `setRect()`.

---

## ✅ Acceptance Criteria

| Check | Status |
|-------|--------|
| When `config.json` declares `parameters`, detailed mode auto-renders controls | ✅ |
| Right-click menu shows 3 styles: Detailed / Square / Circle | ✅ |
| Detailed mode displays 11 parameter control types directly on canvas (no popup) | ✅ |
| Editing parameters on canvas saves to `config.json` in real time | ✅ |
| External edits to `config.json` sync back to canvas controls | ✅ |
| Style switching preserves configuration data | ✅ |
| Node dimensions exact on switch-back (square 140×80, circle 80×80) | ✅ |
| No ProxyWidget residues after any style switch | ✅ |
| All files pass PyLance diagnostics (0 errors) | ✅ |

---

**Updated**: 2026-06-10

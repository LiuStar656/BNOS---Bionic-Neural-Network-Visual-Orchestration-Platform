# 🎨 Drawing Toolbar On-Demand Display

## 🎨 Drawing Toolbar On-Demand Display (2026-06-05)

### Feature Improvement

**Drawing Toolbar On-Demand Display (Enhanced)**
- **Problem**: Drawing toolbar was automatically displayed and fixed on the left side when canvas starts, occupying 36px width of canvas space
- **Fix**: Changed to on-demand display mode, hidden by default, user can toggle display via shortcut key or menu

**New Features**:
- ✅ **Persistence**: Toolbar visibility saved to `canvas_layout.json`, restored after restart
- ✅ **Right-click menu toggle**: Added "Show/Hide Drawing Toolbar" option in canvas context menu

### Technical Implementation

**New Methods** (`draw_layer.py`):
```python
def show_toolbar(self):
    """Show drawing toolbar"""

def hide_toolbar(self):
    """Hide drawing toolbar"""

def toggle_toolbar(self):
    """Toggle drawing toolbar visibility"""
```

**Persistence** (`canvas_layout.py`):
- `save_layout()`: Saves `toolbar_visible` to `canvas_layout.json`
- `load_layout()`: Restores toolbar visibility when loading

**Shortcut Key**:
- `D` key: Toggle drawing toolbar display/hide

**Right-click Menu**:
- "Show Drawing Toolbar"
- "Hide Drawing Toolbar"

**Modified Files**:
- `ui/canvas/draw_layer.py` - Added toolbar toggle methods
- `ui/canvas/canvas_layout.py` - Added toolbar state persistence
- `ui/canvas/canvas_menus.py` - Added right-click menu option
- `ui/canvas/canvas_view.py` - Added toggle method
- `ui/core/strings_cn.json` - Added Chinese translations
- `ui/core/strings_en.json` - Added English translations

### Acceptance Criteria

✅ Canvas starts with drawing toolbar hidden by default
✅ Press `D` key to toggle toolbar display/hide
✅ Hidden toolbar doesn't affect canvas node operations
✅ Hidden toolbar won't be accidentally shown when window resizes
✅ Toolbar visibility persists to `canvas_layout.json`
✅ Right-click menu has "Show/Hide Drawing Toolbar" option
✅ Toolbar state restored after reopening project

---
# Canvas Dock Double-Click Edge Auto-Embed Feature

## 1. Feature Overview

New feature: Double-click on the edge of a floating canvas dock to automatically embed it into the CanvasHost container and hide the title bar for a cleaner canvas view.

## 2. Feature Characteristics

| Feature | Description |
| --- | --- |
| Trigger | Double-click on dock edge area (within 4 pixels) when floating |
| Auto-Embed | Automatically exits floating state and embeds into CanvasHost |
| Title Bar Hide | Title bar automatically hidden after embedding |
| Default Behavior Disabled | Default double-click title bar behavior (maximize/restore) disabled |
| Explicit Restore | `show_title_bar()` method available for explicit restoration |

## 3. Implementation

### 1. Double-Click Event Handling

Detect if double-click position is on edge area in `BnosDock.mouseDoubleClickEvent`:

```python
def mouseDoubleClickEvent(self, event):
    """Double-click event: disable title bar behavior, only allow edge auto-embed"""
    if self._is_floating:
        pos = event.pos()
        border = 4
        w, h = self.width(), self.height()
        
        is_on_edge = (pos.x() < border or pos.x() > w - border or
                     pos.y() < border or pos.y() > h - border)
        
        if is_on_edge:
            self._auto_embed_and_hide_title()
            event.accept()
            return
    
    event.ignore()  # Disable default title bar double-click behavior
```

### 2. Auto-Embed and Title Bar Hide

```python
def _auto_embed_and_hide_title(self):
    """Auto-embed into parent container and hide title bar"""
    if not self.parent() or not hasattr(self.parent(), 'addDockWidget'):
        return
    
    # Exit floating state (embed into parent container)
    self.setFloating(False)
    
    # Hide title bar
    self.hide_title_bar()
```

### 3. Title Bar Management Methods

```python
def hide_title_bar(self):
    """Hide title bar"""
    if self._title_bar_hidden:
        return
    
    self._title_bar_hidden = True
    self.setTitleBarWidget(None)
    self.title_bar_hidden.emit(True)
    self._central_widget.setStyleSheet("background-color: #252526; margin: 0px;")

def show_title_bar(self):
    """Show title bar"""
    if not self._title_bar_hidden:
        return
    
    self._title_bar_hidden = False
    self.setTitleBarWidget(self._title_widget)
    self.title_bar_hidden.emit(False)
```

### 4. New Signal

```python
title_bar_hidden = Signal(bool)  # Title bar visibility change signal
```

## 4. Impact Scope

| File | Changes |
| --- | --- |
| `ui/core/bnos_dock.py` | Added `mouseDoubleClickEvent`, `_auto_embed_and_hide_title`, `hide_title_bar`, `show_title_bar`, `is_title_bar_hidden` methods; added `title_bar_hidden` signal |

## 5. Interaction Flow

1. User drags canvas dock out to floating window
2. User double-clicks on floating window edge (4px range)
3. Dock automatically embeds into CanvasHost container
4. Title bar automatically hidden, canvas occupies full available space
5. Title bar can be explicitly restored via `show_title_bar()`

## 6. Verification

- **Syntax Check**: `python _check_syntax.py` passed
- **Feature Verification Steps**:
  1. Start BNOS, open a project
  2. Drag canvas dock out to floating window
  3. Double-click floating window edge → verify auto-embed and title bar hide
  4. Double-click window interior → verify no embed trigger
  5. Verify title bar remains hidden until explicitly restored

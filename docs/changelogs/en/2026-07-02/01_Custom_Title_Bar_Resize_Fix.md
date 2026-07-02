# Custom Title Bar Window Resize Fix

## Problem

After implementing the custom title bar (`DarkTitleBar` + `FramelessWindowHint`), the main window could not be resized by dragging the edges.

## Root Cause Analysis

After 5 iterations of debugging, two independent root causes were identified:

### 1. `nativeEvent` Shadowed by Python MRO

`BNOSMainWindow`'s multiple inheritance:

```python
class BNOSMainWindow(QMainWindow, ..., MainWindowInteractionMixin):
```

In Python's MRO, `QMainWindow` precedes all Mixins. When Qt calls `nativeEvent`, Python resolves to `QMainWindow.nativeEvent` first. `MainWindowInteractionMixin.nativeEvent` is **never invoked**. The `WM_NCHITTEST` interception logic never took effect.

### 2. `ctypes.MSG` Struct Alignment Causing Wrong Coordinates

Earlier iterations parsed the Windows `MSG` struct via `ctypes` to extract cursor coordinates from `lParam`:

```python
msg = MSG.from_address(int(message))
x = msg.lParam & 0xFFFF
y = (msg.lParam >> 16) & 0xFFFF
```

On 64-bit Windows, the `MSG` struct has implicit alignment padding (4 bytes after `message` to align `wParam`). `ctypes` default alignment does not match the actual memory layout, resulting in misaligned `lParam` values.

Symptoms: top edge could not resize, left edge was not recognized, right and bottom-right detection ranges were offset.

## Fix

### 1. Move `nativeEvent` into the Main Class

Removed `nativeEvent` from `interaction.py` Mixin and placed it directly in `BNOSMainWindow.__main__.py`:

```python
class BNOSMainWindow(QMainWindow, ...):
    def nativeEvent(self, eventType, message):
        ...
```

### 2. Use `QCursor.pos()` Instead of MSG.lParam

Abandoned `ctypes` MSG struct parsing for coordinates, using Qt's high-level API instead:

```python
from PySide6.QtGui import QCursor
cursor_pos = QCursor.pos()
x, y = cursor_pos.x(), cursor_pos.y()
```

Only `MSG_HEADER` (`hwnd` + `message`) is kept for message type detection — these two fields have small offsets unaffected by alignment issues.

### 3. Remove Failed Win32 Hacks

Deleted `_enable_native_resize()` — this method attempted to inject `WS_THICKFRAME` into the `WS_POPUP` window via `SetWindowLongW`, which had no effect on pure `WS_POPUP` windows and caused visual border inconsistency at the top.

A previous `DwmExtendFrameIntoClientArea` attempt also broke resize entirely.

## Modified Files

| File | Change |
|------|--------|
| `ui/main_window/__main__.py` | Added `nativeEvent` method (`WM_NCHITTEST` + `QCursor.pos()`); removed `_enable_native_resize()` |
| `ui/main_window/interaction.py` | Removed dead `nativeEvent` code from Mixin, added comment explaining MRO shadowing |

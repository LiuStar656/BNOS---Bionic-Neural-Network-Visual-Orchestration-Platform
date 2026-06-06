# 🎨 Toast Notification Visual Effects Fix

## 🎨 Toast Notification Visual Effects Fix (2026-06-06)

### Problem Description

**Toast notifications have severe visual defects**
- **Issue 1: Black background flicker** — A black square appears briefly when a toast is first shown, then the correct style is rendered
- **Issue 2: Abrupt disappearance animation** — Toast vanishes instantly instead of fading out smoothly
- **Impact**: Poor user experience, non-smooth visual feedback, inconsistent with BNOS dark theme

### Root Cause Analysis

1. **Conflicting window attributes** — The previous implementation set three mutually conflicting window attributes simultaneously:
   - `WA_StyledBackground`: Tells Qt to paint a solid-color background via QStyle
   - `setAutoFillBackground(True)`: Fills the widget with the default QPalette color (usually black)
   - `WA_TranslucentBackground`: Requests the window to be transparent
   - Together they cause the window to first paint as black, then get overlaid with the rgba style — producing the visible "black flicker"

2. **Wrong animation mechanism** — Using `QGraphicsOpacityEffect` on a stand-alone Tool window has compatibility issues with `WA_TranslucentBackground`, causing the fade-out phase to stall or skip entirely

### Fix Solution

**Adopted a two-layer architecture ("transparent outer window + styled inner label"), matching the proven pattern used by dialog_utils.py / floating_panel.py**

1. **Base class change**: `QLabel` → `QWidget` (serves as the transparent outer container)
2. **Simplified window attributes**: Only set `WA_TranslucentBackground`, **do NOT** set `WA_StyledBackground` or `setAutoFillBackground(True)`
3. **Style delegation**: An inner `QLabel` carries the rgba background + border-radius + text — this is the correct way to get transparent rounded corners in Qt
4. **Animation rewrite**: A `QTimer` drives `setWindowOpacity()` for linear fade in/out (~60fps at 16ms/frame), replacing the unreliable `QGraphicsOpacityEffect`
5. **Optimized show sequence**: Set opacity to 0.0 first, then show, then start fade-in animation — eliminates any "opaque-then-transparent" flicker

### Key Technical Implementation

```python
class ToastNotification(QWidget):

    def __init__(self, message, parent=None, duration=3000, toast_type="info", stack_index=0):
        super().__init__(parent)

        # Only WA_TranslucentBackground — NO WA_StyledBackground, NO setAutoFillBackground
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Outer: zero-margin layout (the window itself paints nothing)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Inner: QLabel carries rgba background + border-radius + text (the key trick)
        self._label = QLabel(message)
        self._label.setStyleSheet(
            "background-color: rgba(76, 175, 80, 230);"
            "color: #ffffff;"
            "padding: 12px 20px;"
            "border-radius: 8px;"
            "font-size: 14px;"
            "font-weight: bold;"
        )
        outer.addWidget(self._label)

        # Animation: QTimer drives setWindowOpacity() (more stable than QGraphicsOpacityEffect)
        self._anim_timer = QTimer(self)
        self._anim_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._anim_timer.timeout.connect(self._tick_animation)

        # Start fully transparent to avoid any "opaque snapshot" on show
        self.setWindowOpacity(0.0)

    def show_toast(self):
        """Key sequence: opacity=0 → show → start fade-in animation"""
        self.setWindowOpacity(0.0)
        self._opacity = 0.0
        self.show()
        self._is_fading_in = True
        self._anim_timer.start(16)
```

### Code Format Optimization

**Animation frame processing readability improvements**
- Added blank lines before `if self._opacity >= 1.0:` and `if self._opacity <= 0.0:` to enhance code readability
- Ensured consistent indentation to avoid potential indentation errors
- Maintained clear code structure for easier future maintenance

### Modified Files

- `ui/core/toast/toast_notification.py` — Fully rewritten with two-layer architecture + setWindowOpacity animation, optimized code formatting

### Acceptance Criteria

✅ No black flicker when a toast appears — it renders directly in its transparent rounded style
✅ Smooth fade-out on disappearance (~300ms), visually natural
✅ Consistent behavior with other working transparent widgets (dialog_utils.py, floating_panel.py)
✅ Supports multiple types (info/success/warning/error) with different colors
✅ Stacking and auto-positioning still works (API unchanged, backward compatible)
✅ Code formatting is consistent and readable, easy to maintain
✅ No regressions introduced

---
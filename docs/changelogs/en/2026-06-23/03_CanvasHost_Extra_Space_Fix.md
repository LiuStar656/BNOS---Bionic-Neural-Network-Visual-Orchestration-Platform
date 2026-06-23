# CanvasHost Extra Space Fix

## 1. Issue Overview

**Description**: Unknown extra space appeared in CanvasHost, occupying part of the canvas area below and affecting user experience.

**Root Cause**: The `central_placeholder` widget created in `_remove_blank_placeholder()` was not properly hidden, causing it to occupy visible space.

## 2. Root Cause Analysis

In `CanvasHost._remove_blank_placeholder()`, a central widget placeholder is required for Qt's Dock system to work correctly. However, the original implementation did not properly set the widget's properties, causing it to occupy visible space:

```python
# Original implementation
central_placeholder = QWidget(self)
central_placeholder.setStyleSheet("background: transparent;")
central_placeholder.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)  # ❌ Not truly hidden
```

Although the background was set to transparent, the widget itself still occupied layout space, resulting in extra blank area.

## 3. Fix Solution

Added proper property settings to `central_placeholder` to ensure it doesn't occupy visible space:

```python
central_placeholder = QWidget(self)
central_placeholder.setStyleSheet("background: transparent;")
central_placeholder.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)  # Transparent background
central_placeholder.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)    # Don't paint opaque areas
central_placeholder.setFixedSize(0, 0)                                            # Fixed size 0
central_placeholder.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)  # Ignore layout policy
```

## 4. Impact Scope

| File | Changes |
| --- | --- |
| `ui/core/canvas_host.py` | Optimized `central_placeholder` widget properties; added `QSizePolicy` import |

## 5. Verification

- **Syntax Check**: `python _check_syntax.py` passed
- **Feature Verification Steps**:
  1. Start BNOS, open a project
  2. Check if there's still extra blank space below canvas area
  3. Verify canvas occupies entire available area
  4. Switch projects or create new project → verify space issue no longer occurs

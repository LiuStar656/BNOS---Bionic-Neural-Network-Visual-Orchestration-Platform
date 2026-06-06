## 🎨 Feature Update: Rect Node Real-time Status Display (2026-06-06)

### New Features
- **Real-time Status Monitoring for Rect Nodes**: Implemented real-time display of CPU, memory, and runtime duration for rectangular nodes
- **Resource Monitoring Module**: Added `node_monitor.py` module to collect real-time resource usage of node processes
- **Status Display Component**: Created `node_status_widget.py` component to visualize node status information

### Technical Implementation
1. **Status Display UI**:
   - CPU usage display (with progress bar)
   - Memory usage display (with progress bar)
   - Runtime duration timer
   - Color-coded visualization: CPU(Cyan), Memory(Red), Duration(Yellow)

2. **Monitoring Mechanism**:
   - Uses psutil library to retrieve system process information
   - Automatically updates status every 2 seconds
   - Only updates nodes within the visible area of the canvas
   - Automatically manages node addition/removal/update

3. **Style Extension**:
   - Added status display related properties in `node_style.py`
   - Rectangular nodes have status display enabled by default
   - Automatically enables/disables status display when switching styles

### File Changes
- `ui/canvas/items/node_style.py`: Added status display properties
- `ui/canvas/items/node_item.py`: Integrated status display component
- `ui/canvas/items/node_status_widget.py`: New status display component
- `ui/core/node_monitor.py`: New node monitoring module

### Feature Highlights
- ✅ Real-time CPU usage display (0-100%)
- ✅ Real-time memory usage display (MB)
- ✅ Real-time runtime duration display (HH:MM:SS)
- ✅ Visual resource usage with progress bars
- ✅ Optimized performance by only updating visible nodes
- ✅ Automatic adaptation when switching node styles
- ✅ Integration with existing node status indicators

## 🔧 Code Robustness Fixes (2026-06-06)

### Fixes
- **QTimer Import Issue**: Added comment in canvas_view.py to clarify QTimer is imported at the top of the file
- **Animation Frame Indentation**: Optimized indentation and readability of animation handling code in toast_notification.py
- **README Rendering Issues**: Fixed table and project structure rendering format in README.md

### File Changes
- `ui/canvas/canvas_view.py`: Added QTimer import comment
- `ui/core/toast/toast_notification.py`: Optimized animation code formatting
- `README.md`: Unified table format and project structure display

## 🎨 Toast Notification Visual Effects Fix (2026-06-06)

### Issue Fixes
1. **Black Border Issue**:
   - Problem: Black square appeared at rounded corners of the window
   - Fix: Adopted double-layer architecture - outer QWidget with only WA_TranslucentBackground, inner QLabel for styling
   - File: `ui/core/toast/toast_notification.py`

2. **Transparency Effect**:
   - Problem: Window did not achieve translucent effect
   - Fix: Removed WA_StyledBackground and setAutoFillBackground(True) to ensure window displays directly with translucent rounded style
   - File: `ui/core/toast/toast_notification.py`

3. **Disappearance Animation**:
   - Problem: Disappearance animation was not a smooth fade-out effect
   - Fix: Implemented linear fade-in/fade-out animation using QTimer-driven setWindowOpacity() instead of QGraphicsOpacityEffect
   - File: `ui/core/toast/toast_notification.py`

### Technical Implementation
- **Double-layer Architecture**: Outer transparent window (QWidget) + inner QLabel for styling
- **Animation Optimization**: Smooth fade-out effect using QTimer and setWindowOpacity(), animation duration ~300ms
- **Compatibility**: Avoided compatibility issues between QGraphicsOpacityEffect and WA_TranslucentBackground on Tool windows

### Acceptance Criteria
- ✅ Window displays directly with translucent rounded style, no black borders
- ✅ Smooth natural show/hide animations, duration ~300ms
- ✅ Tested and verified on different devices and system versions
- ✅ No impact on existing functionality and interface compatibility

### File Changes
- `ui/core/toast/toast_notification.py`: Refactored toast notification component implementation
- `docs/UPDATE_CN.md`: Added fix documentation
- `docs/UPDATE_EN.md`: Added English version fix documentation

---

*Last Updated: 2026-06-06*
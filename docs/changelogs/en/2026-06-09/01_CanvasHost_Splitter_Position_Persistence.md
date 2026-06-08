# 🔧 CanvasHost Splitter Position Persistence Fix

## 📋 Problem Overview

Dock splitter position persistence for the main window was working correctly, but there was an issue with splitter position persistence in the CanvasHost window. After adjusting the size between the canvas and terminal, the previous splitter position could not be remembered after restarting the program, resulting in poor user experience.

## 🔍 Problem Analysis

### Root Causes

1. **CanvasHost is an Independent QMainWindow**
   - CanvasHost has its own Dock system (Canvas Dock, Terminal Dock)
   - Independent layout management and splitter system

2. **Canvas Dock Creation Timing Issue**
   - Canvas Dock is only created when the user opens a project
   - Canvas Dock does not exist at program startup
   - The original restoration flow only executed at program startup, unable to restore CanvasHost

3. **Missing Independent Save/Restore Logic**
   - Only saved the main window's `saveState()`
   - Did not save CanvasHost's `saveState()`
   - Did not save size information for each area in CanvasHost

## ✨ Feature Implementation

### 1. **Enhanced Save Logic**

Modified `ui/core/window_state_manager.py`:
- Added `_collect_canvas_host_area_layouts()` function
- Collects Dock information and sizes for each area in CanvasHost
- Saves CanvasHost's `saveState()` data
- Updated version number to `4.0`

### 2. **Split Restoration Logic**

Window state restoration is divided into two phases:

**Phase A - At Program Startup (Main Window Restoration):**
- Phase 1: Restore main window Qt native state
- Phase 2: First main window size adjustment
- Phase 3: Second main window size adjustment (consolidate splitter position)
- Phase 4: Restore terminal Dock

**Phase B - After Project Opens (CanvasHost Restoration):**
- Phase 5: Restore CanvasHost Qt native state (most critical!)
- Phase 6: First CanvasHost size adjustment
- Phase 7: Second CanvasHost size adjustment (consolidate splitter position)

### 3. **New Independent Restoration Function**

- Added `restore_canvas_host_state()` function
- Called separately after project is opened
- Uses `QTimer.singleShot()` to ensure Dock is fully created before restoration

### 4. **Multi-Scene Coverage**

Ensure the following scenarios can be properly restored:
- Auto-open last project (`_auto_open_project`)
- User manually opens project (`project_open`)

## 🔧 Technical Details

### Modified Files

| File | Description |
|------|-------------|
| `ui/core/window_state_manager.py` | Added CanvasHost save/restore logic |
| `ui/main_window.py` | Call CanvasHost restoration when auto-opening project |
| `ui/core/project_manager.py` | Call CanvasHost restoration when manually opening project |

### Configuration Structure

```json
{
  "dock_layout": {
    "version": "4.0",
    "main_window_state": "...",
    "area_layouts": { ... },
    "canvas_host_state": {
      "qt_state": "base64-encoded saveState() data",
      "area_layouts": {
        "top": {
          "orientation": "horizontal",
          "docks": [ ... ]
        },
        "bottom": {
          "orientation": "horizontal",
          "docks": [
            {
              "title": "Terminal",
              "width": 800,
              "height": 300
            }
          ]
        }
      }
    },
    "terminal_dock": { ... }
  }
}
```

### Core Code Logic

**Save CanvasHost State:**
```python
# Save CanvasHost Qt native state
canvas_host_qt_state = canvas_host.saveState()
canvas_host_state_base64 = base64.b64encode(canvas_host_qt_state).decode('utf-8')

# Collect area layout info in CanvasHost
canvas_host_area_layouts = _collect_canvas_host_area_layouts(canvas_host)

canvas_host_state = {
    "qt_state": canvas_host_state_base64,
    "area_layouts": canvas_host_area_layouts
}
```

**Restore CanvasHost State:**
```python
# First restore Qt native state (includes layout and splitter positions)
canvas_host.restoreState(canvas_host_qt_state)

# Then use resizeDocks() for precise size adjustment
canvas_host.resizeDocks([term_dock], [height], Qt.Orientation.Vertical)
```

## 🎯 Features

✅ **Dual Saving** - Saves both Qt native state and explicit size information
✅ **Correct Timing** - CanvasHost restoration executes after project opens
✅ **Multi-Phase Restoration** - Adjust in phases to ensure correct splitter positions
✅ **Multi-Scene Coverage** - Both auto-open and manual open are restored
✅ **Backward Compatible** - Version number management, old configurations don't break
✅ **Debug Friendly** - Detailed log output

## 🧪 Testing Verification

### Test Cases

1. **Initial State Test**
   - Start software ✅
   - Auto-open last project ✅
   - Verify CanvasHost layout ✅

2. **Splitter Adjustment Test**
   - Drag splitter between canvas and terminal ✅
   - Adjust to different heights ✅

3. **Persistence Test**
   - Adjust splitter position ✅
   - Close software ✅
   - Restart ✅
   - Verify splitter position is maintained ✅

4. **Manual Open Project Test**
   - Open project through menu ✅
   - Verify splitter position is correctly restored ✅

5. **Configuration File Check**
   - Open `app_config.json` ✅
   - Verify `canvas_host_state` field exists ✅
   - Verify size data in `area_layouts` ✅

## 📝 User Guide

### Usage Instructions

1. **Adjust CanvasHost Layout**
   - Drag the splitter between the canvas and terminal
   - Adjust to a comfortable size

2. **Auto-save State**
   - Automatically saved when closing software
   - No manual operation needed

3. **Restart Restoration**
   - Next launch automatically restores last splitter position
   - Size ratio between canvas and terminal remains unchanged

---

**Date**: 2026-06-09
**Updated by**: Trae AI

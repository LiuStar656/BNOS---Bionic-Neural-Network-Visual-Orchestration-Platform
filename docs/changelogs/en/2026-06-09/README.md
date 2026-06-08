# 2026-06-09 Changelog

## 📋 Update Overview

This update mainly fixes the persistence issue of splitter position in the CanvasHost window, ensuring that size adjustments between the canvas and terminal can be correctly saved and restored.

## ✨ Update Contents

### 1. 🔧 CanvasHost Splitter Position Persistence

**Feature Description**:
- CanvasHost window splitter position automatically saved to `app_config.json`
- Auto-restores previous splitter position after project opens
- Supports both auto-open and manual-open project scenarios
- Uses dual save mechanism (Qt native state + explicit sizes) for correctness

**Modified Files**:
- `ui/core/window_state_manager.py`
- `ui/main_window.py`
- `ui/core/project_manager.py`

**Detailed Document**: [CanvasHost Splitter Position Persistence](./01_CanvasHost_Splitter_Position_Persistence.md)

---

## 🎯 Overview

| Feature | Status |
|---------|--------|
| CanvasHost Splitter Position Persistence | ✅ Completed |

---

**Date**: 2026-06-09

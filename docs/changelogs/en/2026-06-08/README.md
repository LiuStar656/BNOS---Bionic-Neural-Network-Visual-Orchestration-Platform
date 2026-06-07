# 2026-06-08 Changelog

## 📋 Overview

This update primarily implements drawing tool display state persistence for improved user experience.

## ✨ Updates

### 1. 🎨 Drawing Tool Display State Persistence

**Description**:
- Drawing toolbar display state automatically saved to `app_config.json`
- Automatically restores last display state after software restart
- Fixed issue requiring two consecutive operations to toggle state

**Modified Files**:
- `ui/core/app_config.py`
- `ui/canvas/draw_layer.py`
- `ui/canvas/canvas_view.py`
- `ui/canvas/canvas_layout.py`

**Detailed Documentation**: [Drawing Tool State Persistence](./01_Drawing_Tool_State_Persistence.md)

---

## 🎯 Overview

| Feature | Status |
|---------|--------|
| Drawing Tool Display State Persistence | ✅ Done |

---

**Date**: 2026-06-08

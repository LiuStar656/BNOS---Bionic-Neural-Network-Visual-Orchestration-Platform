# 【2026-06-14】V2.0.14 - PyQt6 to PySide6 Full-Stack Migration

---

## Update List

### 1. PyQt6 → PySide6 Full-Stack Migration

[View Details](./01_PyQt6_to_PySide6_Migration.md)

- License upgrade: GPL v3 → **LGPL v3**, eliminates closed-source commercial licensing fees
- 100 source files, 233 import replacements
- 66 `pyqtSignal` → `Signal`, 4 `pyqtSlot` → `Slot`
- Zero business logic changes, pure API name mapping
- Signal emit/connect call syntax unchanged

---

## Key Updates

| Category | Details |
|------|----------|
| **Dependency** | PyQt6 → PySide6 6.11.1, requirements.txt updated |
| **Syntax** | pyqtSignal → Signal, pyqtSlot → Slot |
| **Docs** | README/CHANGELOG/i18n strings synced |
| **Build** | build_bnos.spec hiddenimports updated to PySide6 |

---

## Verification Results

- ✅ 169/169 Python source files compiled
- ✅ Startup test: main window, dock panels, canvas, IPC all functional
- ✅ Terminal panel (QProcess) working
- ✅ Node load/stop/monitor working
- ✅ History rollback (undo/redo) working
- ✅ Resource monitoring polling working
- ✅ Window state persistence working
- ✅ `pyqtSignal` / `PyQt6` residuals: 0

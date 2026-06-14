# PyQt6 to PySide6 Full-Stack Migration

## Background

The project previously used **PyQt6** (Riverbank Computing third-party bindings), licensed under GPL v3 / Commercial. For closed-source distribution or commercialization scenarios, this posed license compliance risks (commercial license ~550 GBP/developer).

**PySide6** is the Qt Company's officially maintained Qt for Python binding, licensed under **LGPL v3**, allowing dynamic linking in closed-source applications without commercial licensing fees.

---

## Migration Scope

| Dimension | Data |
|------|------|
| Affected Python source files | **100** |
| Import replacements (`PyQt6` → `PySide6`) | **233** lines |
| Signal declarations (`pyqtSignal` → `Signal`) | **66** occurrences |
| Slot decorators (`pyqtSlot` → `Slot`) | **4** occurrences |
| Documentation/i18n string updates | **16** files |
| Business logic rewrites | **0** |

---

## Replacement Details

### Package Name Replacement

```
PyQt6.QtCore    → PySide6.QtCore
PyQt6.QtGui     → PySide6.QtGui
PyQt6.QtWidgets → PySide6.QtWidgets
PyQt6.QtNetwork → PySide6.QtNetwork
```

### Signal/Slot Syntax Replacement

```python
# Before (PyQt6)
from PyQt6.QtCore import pyqtSignal, pyqtSlot
my_signal = pyqtSignal(str, int)
@pyqtSlot(str)

# After (PySide6)
from PySide6.QtCore import Signal, Slot
my_signal = Signal(str, int)
@Slot(str)
```

### Configuration File Updates

- `requirements.txt`: `pyqt6>=6.4.0` → `pyside6>=6.4.0`
- `build_bnos.spec`: `hiddenimports` updated to PySide6 modules
- `strings_cn.json` / `strings_en.json`: description text updated

---

## Unchanged APIs

The following APIs are identical between PyQt6 and PySide6 and required no changes:

- `signal.emit()` / `signal.connect()` call syntax
- `QApplication.exec()` / `QMenu.exec()`
- `QMessageBox.StandardButton` / `QDialog.DialogCode` enums
- `QFont.setFamilies()` / `QFontDatabase.addApplicationFont()`
- `QProcess` / `QTimer` / `QThread` all APIs
- `QLocalServer` / `QLocalSocket` IPC communication
- `QGraphicsItem` / `QGraphicsView` canvas system APIs
- `QDockWidget` / `QMainWindow` panel system APIs

---

## Migration Verification

| Verification Item | Result |
|--------|:--:|
| Python compilation check (169 source files) | All passed |
| Startup test (main window + dock + canvas + IPC) | Passed |
| Terminal panel (QProcess) | Passed |
| Node load/stop/monitor | Passed |
| History rollback (undo/redo) | Passed |
| Resource monitoring polling | Passed |
| Window state persistence | Passed |
| Toast notifications | Passed |
| `pyqtSignal` / `PyQt6` residuals | 0 |

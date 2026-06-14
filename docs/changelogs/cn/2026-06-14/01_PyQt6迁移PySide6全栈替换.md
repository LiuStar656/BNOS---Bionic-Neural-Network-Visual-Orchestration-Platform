# PyQt6 → PySide6 全栈迁移

## 迁移背景

项目原先使用 **PyQt6**（Riverbank Computing 第三方绑定），其许可证为 GPL v3 / 商业授权。对于需要闭源分发或商业化的场景，存在许可证合规风险（商业授权约 550 GBP/开发者）。

**PySide6** 是 Qt Company 官方维护的 Qt for Python 绑定，许可证为 **LGPL v3**，允许动态链接闭源应用，免除商业许可费用。

---

## 迁移范围

| 维度 | 数据 |
|------|------|
| 受影响的 Python 源文件 | **100 个** |
| import 行替换 (`PyQt6` → `PySide6`) | **233** 处 |
| Signal 声明 (`pyqtSignal` → `Signal`) | **66** 处 |
| Slot 装饰器 (`pyqtSlot` → `Slot`) | **4** 处 |
| 文档/国际化字符串更新 | **16** 个文件 |
| 业务逻辑重写 | **0** 处 |

---

## 替换明细

### 包名替换

```
PyQt6.QtCore    → PySide6.QtCore
PyQt6.QtGui     → PySide6.QtGui
PyQt6.QtWidgets → PySide6.QtWidgets
PyQt6.QtNetwork → PySide6.QtNetwork
```

### 信号/槽语法替换

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

### 配置文件更新

- `requirements.txt`: `pyqt6>=6.4.0` → `pyside6>=6.4.0`
- `build_bnos.spec`: `hiddenimports` 替换为 PySide6 模块
- `strings_cn.json` / `strings_en.json`: 描述文本更新

---

## 无需修改的部分

以下 API 在 PyQt6 与 PySide6 中完全一致，未做任何改动：

- `signal.emit()` / `signal.connect()` 调用语法
- `QApplication.exec()` / `QMenu.exec()`
- `QMessageBox.StandardButton` / `QDialog.DialogCode` 枚举
- `QFont.setFamilies()` / `QFontDatabase.addApplicationFont()`
- `QProcess` / `QTimer` / `QThread` 全部 API
- `QLocalServer` / `QLocalSocket` IPC 通信
- `QGraphicsItem` / `QGraphicsView` 画布系统 API
- `QDockWidget` / `QMainWindow` 面板系统 API

---

## 迁移验证

| 验证项 | 结果 |
|--------|:--:|
| Python 编译检查 (169 个源文件) | 全部通过 |
| 启动测试（主窗口 + Dock + 画布 + IPC） | 通过 |
| 终端面板 (QProcess) | 通过 |
| 节点加载/停止/监控 | 通过 |
| 历史回滚 (undo/redo) | 通过 |
| 资源监测轮询 | 通过 |
| 窗口状态持久化 | 通过 |
| Toast 通知 | 通过 |
| `pyqtSignal` / `PyQt6` 残留 | 0 |

# Dock 窗口吸附 Bug 修复与边缘判定优化

## 一、问题概述

### Bug 1：Dock 窗口拖出再吸附导致界面消失
- **问题描述**：当用户将画布 Dock 拖出成为浮动窗口后，再将其吸附回主窗口时，整个软件界面会直接消失，但进程仍在运行。
- **复现步骤**：拖出画布 Dock → 再次拖回并吸附 → 界面消失

### Bug 2：边缘尺寸控制判定范围过大
- **问题描述**：Dock 窗口边缘拖拽调整尺寸的判定区域（border）设置为 6 像素，范围过大导致用户在靠近窗口边缘操作时容易误触尺寸调整功能。

## 二、根因分析

### Bug 1 根因

在 `BnosDock._on_top_level_changed` 方法中，当从漂浮状态变回停靠状态时，代码错误地操作了 `self.window()`：

```python
def _on_top_level_changed(self, floating):
    self._is_floating = floating
    if floating:
        QTimer.singleShot(0, self._apply_floating_style)
    else:
        w = self.window()  # ❌ 错误：当QDockWidget漂浮时，window()返回Qt创建的内部容器窗口
        w.setWindowFlags(w.windowFlags() & ~Qt.WindowType.FramelessWindowHint)
        ...
```

当 QDockWidget 漂浮时，Qt 会创建一个内部容器窗口，`self.window()` 返回的是这个临时容器窗口。当 dock 被吸附回去时，这个容器窗口可能已被销毁或变成无效对象，导致设置窗口标志失败，进而导致整个软件界面消失。

### Bug 2 根因

`border = 6` 的判定范围在高分辨率屏幕上显得过大，用户靠近窗口边缘进行正常操作时容易误触尺寸调整功能，影响用户体验。

## 三、修复方案

### Bug 1 修复

将操作对象从 `self.window()` 改为直接操作 `self`：

```python
def _on_top_level_changed(self, floating):
    """漂浮状态切换回调"""
    self._is_floating = floating
    if floating:
        QTimer.singleShot(0, self._apply_floating_style)
    else:
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.FramelessWindowHint)
        self._apply_docked_style()
        self.show()
```

此修复与 `BnosDockWidget`（用于普通面板）保持一致，避免操作已销毁的内部容器窗口。

### Bug 2 修复

将边缘判定范围从 6 像素调整为 4 像素：

**修改文件：**
- `ui/core/bnos_dock.py`：`border = 6` → `border = 4`
- `ui/core/dock_manager.py`：`border = 6` → `border = 4`

## 四、影响范围

| 文件 | 变更点 |
| --- | --- |
| `ui/core/bnos_dock.py` | `_on_top_level_changed` 中操作对象改为 `self`；`border` 从 6 改为 4 |
| `ui/core/dock_manager.py` | `border` 从 6 改为 4 |

## 五、验证

- **语法检查**：`python _check_syntax.py` 通过
- **功能验证步骤**：
  1. 启动 BNOS，打开一个项目
  2. 将画布 Dock 拖出成为浮动窗口
  3. 将浮动窗口拖回主窗口并吸附 → 验证界面不会消失
  4. 多次重复步骤 2-3 → 验证稳定性
  5. 在不同屏幕分辨率下测试边缘拖拽功能 → 验证判定范围适中，不易误触

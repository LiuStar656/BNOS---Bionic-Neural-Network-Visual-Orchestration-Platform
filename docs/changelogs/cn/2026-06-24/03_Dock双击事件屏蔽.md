# 03 Dock 双击事件屏蔽

## 问题概述

双击 Dock 窗口标题栏切换浮动/停靠的功能存在 Bug，暂时屏蔽。

## 根因分析

最初使用 `event.ignore()` 试图屏蔽双击事件，但 `ignore()` 只是将事件标记为"未处理"并继续向上传播给 Qt 的 Dock 系统，Qt 内部仍会触发浮动/停靠切换，无法真正屏蔽。

## 解决方案

采用**双重拦截**机制：

1. **事件过滤器层**：`self.installEventFilter(self)` 在事件分发最早阶段拦截 `QEvent.MouseButtonDblClick`，返回 `True` 吞噬事件，阻止传播到 Qt 内部
2. **mouseDoubleClickEvent 层**：改为 `event.accept()` 作为兜底，确保事件被消费

同时：
- `DockDoubleClickHandler` 清空实现，仅保留类定义并标记 `[已禁用]`
- 移除两个 Dock 类中的 handler 初始化
- `BnosDock._on_before_embed` 注释保留，便于后续恢复

## 影响范围

| 文件 | 变更类型 |
|------|---------|
| `ui/core/dock_position_manager.py` | `DockDoubleClickHandler` 类清空并标记禁用 |
| `ui/core/bnos_dock.py` | 添加 `QEvent` 导入；安装 `eventFilter` 拦截双击；`mouseDoubleClickEvent` → `accept()`；移除 handler 初始化；注释 `_on_before_embed` |
| `ui/core/dock_manager.py` | 同上 |

## 验证方式

- 双击 Dock 标题栏 → 无任何响应（不切换浮动/停靠）
- 双击 Dock 边缘区域 → 无任何响应
- 通过拖动标题栏仍可正常浮动/停靠

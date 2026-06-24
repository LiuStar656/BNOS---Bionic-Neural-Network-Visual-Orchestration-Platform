# 02 Dock 双击事件组件化

## 问题概述

`BnosDock`（bnos_dock.py）和 `BnosDockWidget`（dock_manager.py）中各自包含一段近 30 行的 `mouseDoubleClickEvent` 重复代码，逻辑完全相同（判断边缘/标题栏点击 → 切换浮动/停靠），仅嵌入时的回调差异（BnosDock 需先隐藏标题栏）。

## 根因分析

双击 Dock 标题栏/边缘切换浮动停靠的逻辑散落在两个 QDockWidget 子类中，缺乏统一抽象。每当需要修改双击行为时，必须同时修改两处代码，维护成本高且容易遗漏。

## 解决方案

1. **新增 `DockDoubleClickHandler` 组件**（位于 `ui/core/dock_position_manager.py`）：
   - 独立的 `QObject` 子类，统一处理双击标题栏/边缘事件
   - 通过 `handle(event)` 方法返回 `True`/`False` 表示是否已处理
   - 通过构造函数注入 `title_widget_getter`、`is_title_bar_hidden`、`on_before_embed` 三个回调，适配不同 Dock 子类的差异
   - 与 `DockPositionManager` 紧耦合：嵌入时自动调用 `save_current_state_before_toggle()` + `restore_to_docked_position()`

2. **`BnosDock` 适配**：
   - `mouseDoubleClickEvent` 从 ~25 行精简为 4 行委托调用
   - 原 `_auto_embed_and_hide_title` 改为 `_on_before_embed` 回调，由 handler 在嵌入前调用

3. **`BnosDockWidget` 适配**：
   - `mouseDoubleClickEvent` 同样精简为委托调用
   - 不需要 `on_before_embed`（面板 Dock 嵌入时不隐藏标题栏）
   - 删除 `_auto_embed` 方法

## 影响范围

| 文件 | 变更类型 |
|------|---------|
| `ui/core/dock_position_manager.py` | 新增 `DockDoubleClickHandler` 类（~70 行） |
| `ui/core/bnos_dock.py` | `mouseDoubleClickEvent` 委托化；`_auto_embed_and_hide_title` → `_on_before_embed` |
| `ui/core/dock_manager.py` | `mouseDoubleClickEvent` 委托化；删除 `_auto_embed` |

## 验证方式

- 画布 Dock：双击标题栏/边缘 → 浮动 ↔ 嵌入（嵌入时隐藏标题栏）
- 面板 Dock：双击标题栏/边缘 → 浮动 ↔ 嵌入（嵌入时保留标题栏）
- 停靠位置恢复准确，不受 Qt 缓存影响

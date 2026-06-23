# Dock 浮动窗口拖动后双击嵌入位置异常问题分析

## 一、问题概述

### 现象

| 操作方式 | 结果 |
|----------|------|
| 停靠状态 → 双击标题栏变悬浮 → **不拖动** → 双击标题栏嵌入 | 正确回到原停靠位置 |
| 停靠状态 → 双击标题栏变悬浮 → **拖动改变悬浮窗口位置** → 双击标题栏嵌入 | 先停靠在当前悬浮窗口的右下角，拖动其他 dock 后才动画平移到正确位置 |
| 停靠状态 → 鼠标拖动出主窗口变悬浮 → 拖动改变悬浮窗口位置 → 双击标题栏嵌入 | 同上，先停靠在右下角 |

### 受影响的组件

- `BnosDock`（画布 Dock，位于 `ui/core/bnos_dock.py`）
- `BnosDockWidget`（主窗口面板 Dock，位于 `ui/core/dock_manager.py`）

---

## 二、根因分析

### 2.1 Qt 原生 QDockWidget 的局限性

Qt 的 `QDockWidget` 有一个**内部缓存**保存"最后停靠区域"。关键行为：

1. **未拖动悬浮窗口**：Qt 保留内部停靠缓存，`setFloating(False)` 直接归位 — **正常**
2. **拖动过悬浮窗口**：Qt 检测到 `moveEvent`，清空内部停靠缓存 — **丢失位置信息**

清空后，`setFloating(False)` 只能根据**浮动窗口当前屏幕坐标**来推测停靠区域，默认选择区域的右下角空位。

### 2.2 之前尝试过但未成功的方案

| 方案 | 方法 | 失败原因 |
|------|------|----------|
| 延迟恢复 | `QTimer.singleShot(100ms, 恢复)` | Qt 布局已固化，时序竞争 |
| 隐藏后恢复 | `hide()` → `removeDockWidget` → `addDockWidget` → `show()` | Qt 排队的布局请求覆盖了后续操作 |
| setUpdatesEnabled 抑制动画 | `setUpdatesEnabled(False)` → 操作 → `setUpdatesEnabled(True)` | `setFloating(False)` 排队的"右下角"布局请求在 `setUpdatesEnabled(True)` 时仍然执行 |
| processEvents 清队列 | 在关键步骤间插入 `processEvents()` | 一个 `processEvents()` 不足以完全清空 Qt 内部排队事件 |
| eventFilter 提前保存 | 鼠标按下时保存停靠区域 | 保存成功但恢复时仍被 Qt 覆盖 |

### 2.3 最终采用的方案：`QDockWidget.setDockLocation()`

这是 Qt 的**原生 API**。在 `setFloating(False)` 之前调用 `setDockLocation(area)`，Qt 会使用指定的区域而不是用浮动窗口位置推测。

```python
# dock_position_manager.py - restore_to_docked_position()
area = self._original_dock_area
if area is None:
    area = self._get_persisted_docked_area()

self._dock_widget.setDockLocation(area)  # 告诉 Qt 目标区域
self._dock_widget.setFloating(False)      # Qt 直接用指定区域停靠
```

### 2.4 配套机制：JSON 文件持久化

创建了独立的 `DockPositionManager`（`ui/core/dock_position_manager.py`）：

```
.bnos/dock_positions.json
{
  "资源监测(Dock)": {
    "docked_area": 1,           // 1=左侧, 2=右侧, 4=顶部, 8=底部
    "floating": {
      "x": 500, "y": 300,
      "width": 400, "height": 300
    }
  }
}
```

**各时机写入规则**：

| 时机 | 写入内容 | 说明 |
|------|----------|------|
| `dockLocationChanged` 信号 | `docked_area` | 拖拽停靠到新区域时立即写入 |
| 浮动窗口拖动（500ms 定时器） | `floating` 坐标 | 实时追踪浮动窗口位置 |
| 双击切换前 `save_current_state_before_toggle()` | 当前状态全量 | 先写 JSON 再切换，防止 Qt 清缓存 |

**屏蔽机制**：恢复期间 `_block_persist = True`，防止 `setFloating(False)` 触发的 `dockLocationChanged` 覆盖正确值。

---

## 三、涉及的关键文件

| 文件 | 角色 |
|------|------|
| `ui/core/dock_position_manager.py` | **核心**：位置持久化、信号监听、恢复逻辑 |
| `ui/core/bnos_dock.py` | 画布 Dock 封装，双击时委托 `DockPositionManager` |
| `ui/core/dock_manager.py` | 主窗口面板 Dock 封装，同样委托 `DockPositionManager` |
| `ui/core/canvas_host.py` | 创建画布 Dock 时调用 `save_original_dock_info` |
| `ui/dialogs/color_settings_dialog.py` | 颜色设置需同时影响两类 Dock |

---

## 四、当前状态：仍未修复

**`setDockLocation()` 方案尚未验证是否解决问题。** 

该 API 的文档描述为：设置 dock 的当前停靠位置。但文档同时指出该值仅在 dock 位于 `QMainWindow` 中时有意义。在浮动状态下调用 `setDockLocation()` 的效果缺乏官方明确说明。

### 可能的下一步方向

1. **验证 `setDockLocation()` 在浮动状态下的行为**：通过日志确认调用后 Qt 内部状态是否正确
2. **尝试 `QDockWidget.DockWidgetFeature` 方案**：在嵌入前临时禁用 `DockWidgetFloatable` 特性
3. **尝试 `QMainWindow.saveState()` / `restoreState()` 方案**：停靠时保存布局快照，嵌入时恢复
4. **升级 PySide6 版本**：检查是否有相关 bug 修复
5. **向 Qt/PySide6 提交 bug report**：如果确认是框架层面问题

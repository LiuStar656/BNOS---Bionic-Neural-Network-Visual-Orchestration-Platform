# Dock 窗口尺寸持久化问题记录

## 问题描述
调整 Dock 窗口尺寸后，重启应用，尺寸没有正确保持。

## 当前状态
- ✅ 尺寸已正确保存到 `app_config.json`
- ❌ 尺寸恢复时没有正确应用

## 日志分析

### 保存阶段（成功）
```
[01:25:54] INFO  💾 ===== 开始保存窗口状态 =====
[01:25:54] INFO  💾 找到 4 个 Dock 窗口
[01:25:54] INFO  💾 主窗口 Dock 尺寸已保存: {
  '终端': {'floating': False, 'width': 1534, 'height': 472},
  '3': {'floating': False, 'width': 1534, 'height': 562},
  '节点列表(Dock)': {'floating': False, 'width': 380, 'height': 610},
  '资源监测(Dock)': {'floating': False, 'width': 380, 'height': 424}
}
[01:25:54] INFO  💾 终端 Dock 尺寸已保存: {'floating': False, 'width': 1534, 'height': 472}
[01:25:54] INFO  💾 ===== 窗口状态已保存 =====
```

### 恢复阶段（部分成功）
```
[01:25:48] INFO  📐 [300ms] 开始恢复主窗口 Dock 尺寸
[01:25:48] INFO  📐 [300ms] 从配置读取 main_dock_sizes: {
  '终端': {'floating': False, 'width': 1534, 'height': 184},
  '3': {'floating': False, 'width': 1534, 'height': 850},
  '节点列表(Dock)': {'floating': False, 'width': 380, 'height': 610},
  '资源监测(Dock)': {'floating': False, 'width': 380, 'height': 424}
}
[01:25:48] INFO  📐 [300ms] 主窗口找到 1 个 Dock
[01:25:48] INFO  📐 [300ms] 恢复 Dock 0: 终端
```

## 问题分析

### 发现的问题
1. **只找到 1 个 Dock**：恢复时说"主窗口找到 1 个 Dock"，但保存时找到 4 个 Dock
2. **终端 Dock 被重复保存**：既在 `main_dock_sizes` 里，又单独在 `terminal_dock_size` 里
3. **恢复时机问题**：Dock 窗口可能还没完全创建就尝试恢复尺寸

### 可能的原因
1. **Dock 位置问题**：终端 Dock 在 CanvasHost 里，不在主窗口里
2. **恢复时机**：恢复时部分 Dock 还没创建完成
3. **Dock 名称匹配**：保存和恢复时的 Dock 名称可能不一致

## 已完成的修复

### 1. 修复 `int(dock_area)` 错误
**文件**：`ui/core/window_state_manager.py`
**问题**：尝试将 `DockWidgetArea` 枚举对象转换为 int 导致错误
**修复**：删除了 `dock_area` 字段，只保存必要的尺寸信息

### 2. 优化关闭和重启流程
**文件**：`ui/main_window.py`
**改进**：
- 清晰的三阶段结构（保存 → 断开 → 关闭/重启）
- 更详细的日志追踪
- 确保所有数据保存完成后再执行关闭

### 3. 窗口状态管理重写
**文件**：`ui/core/window_state_manager.py`
**改进**：
- 删除对 `QMainWindow.saveState/restoreState` 的依赖
- 直接手动保存和恢复每个 Dock 的尺寸
- 保存到 `app_config.json` 的 `main_dock_sizes` 和 `terminal_dock_size` 配置项

## 待解决问题

### 1. Dock 查找问题
```
[01:25:48] INFO  📐 [300ms] 主窗口找到 1 个 Dock
```
但保存时找到 4 个 Dock。需要检查：
- 为什么只找到 1 个 Dock？
- 其他 Dock 在哪里？在 CanvasHost 里？

### 2. 终端 Dock 重复保存
终端 Dock 既在 `main_dock_sizes` 里，又在 `terminal_dock_size` 里，需要统一。

### 3. 尺寸恢复逻辑
当前的 `_restore_dock_size` 函数：
```python
def _restore_dock_size(dock, size_info, parent_window):
    if not dock or not size_info:
        return
    
    floating = size_info.get("floating", False)
    dock.setFloating(floating)
    
    if floating:
        x = size_info.get("x")
        y = size_info.get("y")
        width = size_info.get("width")
        height = size_info.get("height")
        if all(v is not None for v in [x, y, width, height]):
            dock.setGeometry(x, y, width, height)
    else:
        width = size_info.get("width")
        height = size_info.get("height")
        
        if width and height:
            dock.resize(width, height)
            parent_window.update()
```

可能的问题：
- `dock.resize()` 对停靠的 Dock 可能不起作用
- 需要使用 `QMainWindow.resizeDocks()` 来调整停靠的 Dock 尺寸

## 下一步计划

### 方案 1：使用 `resizeDocks`（推荐）
对于停靠在同一区域的 Dock，使用 `QMainWindow.resizeDocks()` 来调整尺寸：
```python
def _restore_dock_size(dock, size_info, parent_window):
    if not dock or not size_info:
        return
    
    floating = size_info.get("floating", False)
    dock.setFloating(floating)
    
    if floating:
        x = size_info.get("x")
        y = size_info.get("y")
        width = size_info.get("width")
        height = size_info.get("height")
        if all(v is not None for v in [x, y, width, height]):
            dock.setGeometry(x, y, width, height)
    else:
        width = size_info.get("width")
        height = size_info.get("height")
        
        if width and height:
            # 获取 Dock 的停靠区域
            area = parent_window.dockWidgetArea(dock)
            if area in [Qt.DockWidgetArea.LeftDockWidgetArea, Qt.DockWidgetArea.RightDockWidgetArea]:
                # 左右停靠，调整宽度
                parent_window.resizeDocks([dock], [width], Qt.Orientation.Horizontal)
            elif area in [Qt.DockWidgetArea.TopDockWidgetArea, Qt.DockWidgetArea.BottomDockWidgetArea]:
                # 上下停靠，调整高度
                parent_window.resizeDocks([dock], [height], Qt.Orientation.Vertical)
```

### 方案 2：延迟恢复
确保所有 Dock 都创建完成后再恢复尺寸，可以延长延迟时间：
```python
QTimer.singleShot(500, _restore_main_dock_sizes)  # 从 300ms 改为 500ms
QTimer.singleShot(700, _restore_terminal_dock_size)  # 从 500ms 改为 700ms
```

### 方案 3：统一 Dock 管理
将所有 Dock（包括终端 Dock）统一管理，避免重复保存。

## 相关文件

- `ui/core/window_state_manager.py` - 窗口状态管理
- `ui/main_window.py` - 主窗口
- `ui/core/canvas_host.py` - CanvasHost（包含终端 Dock）
- `ui/core/terminal/terminal_dock.py` - 终端 Dock

## 记录日期
2026-06-08

## 记录人
Trae AI

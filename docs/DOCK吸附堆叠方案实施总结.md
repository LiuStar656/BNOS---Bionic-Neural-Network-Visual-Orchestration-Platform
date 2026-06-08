# Dock 吸附堆叠尺寸持久化方案 - 实施总结

## 概述
本文档总结了针对 Qt Dock 吸附堆叠后尺寸分配和持久化问题的解决方案实施情况。

## 实施的更改

### 1. 增强的 WindowStateManager (`ui/core/window_state_manager.py`)

**主要功能：**
- 结合 Qt 原生的 `saveState()` 和 `restoreState()` 保存和恢复布局
- 同时保存自定义的 Dock 详细信息（尺寸、可见性、位置等）
- 使用 `resizeDocks()` 替代直接 `resize()` 来调整停靠 Dock 的尺寸
- 分阶段恢复机制，确保正确的时序

**保存的数据结构：**
```json
{
  "dock_layout": {
    "version": "1.0",
    "qt_state": "base64编码的Qt状态",
    "docks": [
      {
        "title": "面板标题",
        "floating": false,
        "visible": true,
        "area": "left",
        "size": {"width": 300, "height": 500}
      }
    ],
    "terminal_dock": {
      "visible": true,
      "floating": false,
      "size": {"width": 1500, "height": 200}
    }
  }
}
```

### 2. 增强的 DockManager (`ui/core/dock_manager.py`)

**新增功能：**
- `_dock_info_map`：按标题跟踪所有 Dock 信息
- `get_dock_by_title(title)`：按标题查找 Dock
- `get_all_dock_titles()`：获取所有 Dock 标题
- 自动清理已移除 Dock 的信息映射

### 3. 时序优化 (`ui/main_window.py`)

**调整：**
- 将 `_restore_panel_state()` 的调用从 600ms 提前到 50ms
- 确保在 Qt 状态恢复之前，所有需要的 Dock 都已创建完成

## 恢复流程

```
应用启动
  ↓
UI 初始化
  ↓
50ms: _restore_panel_state() → 创建所有 Dock
  ↓
100ms: _restore_phase1() → 恢复 Qt 原生状态
  ↓
200ms: _restore_phase2() → 调整 Dock 尺寸
  ↓
300ms: _restore_phase3() → 恢复终端 Dock
```

## 关键技术点

### 1. 使用 resizeDocks 替代 resize

对于停靠的 Dock，直接调用 `resize()` 通常不起作用。应该使用：
```python
# 左右停靠（调整宽度）
main_window.resizeDocks([dock1, dock2], [width1, width2], Qt.Orientation.Horizontal)

# 上下停靠（调整高度）
main_window.resizeDocks([dock1, dock2], [height1, height2], Qt.Orientation.Vertical)
```

### 2. Qt saveState/restoreState 的作用

Qt 的 `saveState()` 会保存：
- Dock 的停靠位置
- Dock 的堆叠关系（标签页）
- 分割条位置

但不会保存：
- 精确的尺寸（有时）
- 可见性状态

所以需要结合自定义保存机制。

### 3. 分阶段恢复的重要性

必须确保：
1. Dock 先被创建
2. 再恢复 Qt 状态
3. 最后调整尺寸

否则 Qt 的 `restoreState()` 无法正确工作。

## 向后兼容

方案完全支持向后兼容：
- 如果检测不到新版格式（`dock_layout.version == "1.0"`），自动回退到简单恢复逻辑
- 旧的配置项（`main_dock_sizes`、`terminal_dock_size`）仍然被支持

## 测试建议

### 测试场景

1. **单个 Dock 测试**
   - 打开节点列表面板
   - 调整宽度
   - 重启应用，验证尺寸是否恢复

2. **多个 Dock 测试**
   - 同时打开节点列表和资源监测面板
   - 调整它们的尺寸
   - 重启验证

3. **堆叠 Dock 测试**
   - 将两个面板拖到同一区域形成标签页
   - 重启验证堆叠关系和尺寸

4. **浮动 Dock 测试**
   - 将面板拖出为浮动窗口
   - 调整位置和大小
   - 重启验证

5. **终端 Dock 测试**
   - 显示/隐藏终端
   - 调整终端高度
   - 重启验证

## 文件清单

**修改的文件：**
1. `ui/core/window_state_manager.py` - 完全重写，增强版状态管理
2. `ui/core/dock_manager.py` - 添加 Dock 信息跟踪功能
3. `ui/main_window.py` - 优化恢复时序

**新增的文档：**
1. `docs/Dock吸附堆叠尺寸持久化方案.md` - 完整方案设计文档
2. `docs/DOCK吸附堆叠方案实施总结.md` - 本文档

## 参考

- Photoshop 面板管理经验
- Qt QDockWidget 官方文档
- Qt MainWindow 布局保存机制

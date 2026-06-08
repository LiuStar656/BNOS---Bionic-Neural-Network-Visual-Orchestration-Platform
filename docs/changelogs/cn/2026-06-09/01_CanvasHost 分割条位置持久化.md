# 🔧 CanvasHost 分割条位置持久化修复

## 📋 问题概述

主窗口的 Dock 分割条位置持久化已经正常工作，但 CanvasHost 窗口中的分割条位置持久化存在问题。调整画布和终端之间的尺寸后，重启程序无法记住上次的分割条位置，用户体验不佳。

## 🔍 问题分析

### 根本原因

1. **CanvasHost 是独立的 QMainWindow**
   - CanvasHost 内部有自己的 Dock 系统（画布 Dock、终端 Dock）
   - 独立的布局管理和分割条系统

2. **画布 Dock 创建时序问题**
   - 画布 Dock 是在用户打开项目时才创建的
   - 程序启动时画布 Dock 还不存在
   - 原来的恢复流程只在程序启动时执行，无法恢复 CanvasHost

3. **缺少独立的保存/恢复逻辑**
   - 原来只保存了主窗口的 `saveState()`
   - 没有保存 CanvasHost 的 `saveState()`
   - 没有保存 CanvasHost 中各区域的尺寸信息

## ✨ 功能实现

### 1. **保存逻辑增强**

修改 `ui/core/window_state_manager.py`：
- 新增 `_collect_canvas_host_area_layouts()` 函数
- 收集 CanvasHost 中各区域的 Dock 信息和尺寸
- 保存 CanvasHost 的 `saveState()` 数据
- 将版本号更新为 `4.0`

### 2. **恢复逻辑拆分**

将窗口状态恢复分为两个阶段：

**阶段 A - 程序启动时（主窗口恢复）：**
- 阶段 1：恢复主窗口的 Qt 原生状态
- 阶段 2：第一次调整主窗口尺寸
- 阶段 3：第二次调整主窗口尺寸（巩固分割条位置）
- 阶段 4：恢复终端 Dock

**阶段 B - 项目打开后（CanvasHost 恢复）：**
- 阶段 5：恢复 CanvasHost 的 Qt 原生状态（最关键！）
- 阶段 6：第一次调整 CanvasHost 尺寸
- 阶段 7：第二次调整 CanvasHost 尺寸（巩固分割条位置）

### 3. **新增独立恢复函数**

- 新增 `restore_canvas_host_state()` 函数
- 在项目打开后单独调用
- 使用 `QTimer.singleShot()` 确保 Dock 完全创建后再恢复

### 4. **多场景覆盖**

确保以下场景都能正确恢复：
- 自动打开上次项目（`_auto_open_project`）
- 用户手动打开项目（`project_open`）

## 🔧 技术细节

### 修改的文件

| 文件 | 说明 |
|------|------|
| `ui/core/window_state_manager.py` | 新增 CanvasHost 保存/恢复逻辑 |
| `ui/main_window.py` | 自动打开项目时调用 CanvasHost 恢复 |
| `ui/core/project_manager.py` | 手动打开项目时调用 CanvasHost 恢复 |

### 配置结构

```json
{
  "dock_layout": {
    "version": "4.0",
    "main_window_state": "...",
    "area_layouts": { ... },
    "canvas_host_state": {
      "qt_state": "base64 编码的 saveState() 数据",
      "area_layouts": {
        "top": {
          "orientation": "horizontal",
          "docks": [ ... ]
        },
        "bottom": {
          "orientation": "horizontal",
          "docks": [
            {
              "title": "终端",
              "width": 800,
              "height": 300
            }
          ]
        }
      }
    },
    "terminal_dock": { ... }
  }
}
```

### 核心代码逻辑

**保存 CanvasHost 状态：**
```python
# 保存 CanvasHost 的 Qt 原生状态
canvas_host_qt_state = canvas_host.saveState()
canvas_host_state_base64 = base64.b64encode(canvas_host_qt_state).decode('utf-8')

# 收集 CanvasHost 中的区域布局信息
canvas_host_area_layouts = _collect_canvas_host_area_layouts(canvas_host)

canvas_host_state = {
    "qt_state": canvas_host_state_base64,
    "area_layouts": canvas_host_area_layouts
}
```

**恢复 CanvasHost 状态：**
```python
# 先恢复 Qt 原生状态（包含布局和分割条位置）
canvas_host.restoreState(canvas_host_qt_state)

# 再用 resizeDocks() 精确调整尺寸
canvas_host.resizeDocks([term_dock], [height], Qt.Orientation.Vertical)
```

## 🎯 功能特性

✅ **双重保存** - 同时保存 Qt 原生状态和显式尺寸信息
✅ **时序正确** - CanvasHost 恢复在项目打开后执行
✅ **多阶段恢复** - 分阶段调整，确保分割条位置正确
✅ **多场景覆盖** - 自动打开和手动打开都能恢复
✅ **向后兼容** - 版本号管理，旧配置不报错
✅ **调试友好** - 详细的日志输出

## 🧪 测试验证

### 测试用例

1. **初始状态测试**
   - 启动软件 ✅
   - 自动打开上次项目 ✅
   - 检查 CanvasHost 布局 ✅

2. **分割条调整测试**
   - 拖动画布和终端之间的分割条 ✅
   - 调整到不同的高度 ✅

3. **持久化测试**
   - 调整分割条位置 ✅
   - 关闭软件 ✅
   - 重新启动 ✅
   - 检查分割条位置是否保持 ✅

4. **手动打开项目测试**
   - 通过菜单打开项目 ✅
   - 检查分割条位置是否正确恢复 ✅

5. **配置文件检查**
   - 打开 `app_config.json` ✅
   - 查看 `canvas_host_state` 字段是否存在 ✅
   - 查看 `area_layouts` 中的尺寸数据 ✅

## 📝 用户指南

### 使用方法

1. **调整 CanvasHost 布局**
   - 拖动画布和终端之间的分割条
   - 调整到舒适的尺寸

2. **状态自动保存**
   - 关闭软件时自动保存
   - 无需手动操作

3. **重启恢复**
   - 下次启动时自动恢复上次的分割条位置
   - 画布和终端的尺寸比例保持不变

---

**更新日期**：2026-06-09
**更新人**：Trae AI

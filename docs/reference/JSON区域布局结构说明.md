# app_config.json 区域布局数据结构说明（v2.0）

## 概述
从版本 2.0 开始，我们在 `app_config.json` 中**显式保存区域布局信息**，包括每个区域的 Dock 列表和尺寸。这样可以更精确地恢复分割条位置。

## 完整的数据结构

```json
{
  "dock_layout": {
    "version": "2.0",
    "qt_state": "base64编码的Qt状态...",
    "docks": [...],
    "area_layouts": {
      "left": {
        "orientation": "horizontal",
        "docks": [
          {
            "title": "节点列表(Dock)",
            "width": 300,
            "height": 500,
            "visible": true
          },
          {
            "title": "资源监测(Dock)",
            "width": 300,
            "height": 400,
            "visible": true
          }
        ]
      },
      "right": {
        "orientation": "horizontal",
        "docks": [
          {
            "title": "节点监测(Dock)",
            "width": 280,
            "height": 600,
            "visible": true
          }
        ]
      },
      "bottom": {
        "orientation": "vertical",
        "docks": [
          {
            "title": "终端(Dock)",
            "width": 1500,
            "height": 200,
            "visible": true
          }
        ]
      }
    },
    "terminal_dock": {...}
  }
}
```

## 字段详细说明

### 1. `area_layouts`（新增）
这是一个对象，键是区域名称（`left`, `right`, `top`, `bottom`），值是该区域的布局信息。

### 2. 每个区域的布局信息

```json
{
  "orientation": "horizontal",  // 或 "vertical"
  "docks": [...]
}
```

#### `orientation`
- **`horizontal`**: 左右区域（left, right），调整宽度
- **`vertical`**: 上下区域（top, bottom），调整高度

#### `docks`
该区域内的 Dock 列表（按顺序），每个 Dock 包含：
- `title`: Dock 标题
- `width`: 宽度
- `height`: 高度
- `visible`: 是否可见

## 两个 Dock 上下堆叠的例子

假设你将"节点列表"和"资源监测"都拖到左侧区域，形成上下堆叠，调整分割条后保存：

```json
{
  "area_layouts": {
    "left": {
      "orientation": "vertical",  // 注意：虽然是 left 区域，但因为是上下堆叠，orientation 是 vertical！
      "docks": [
        {
          "title": "节点列表(Dock)",
          "width": 300,
          "height": 450,  // 上面的 Dock 高度
          "visible": true
        },
        {
          "title": "资源监测(Dock)",
          "width": 300,
          "height": 350,  // 下面的 Dock 高度
          "visible": true
        }
      ]
    }
  }
}
```

**关键点**：
- 即使是 `left` 区域，如果 Dock 是**上下堆叠**，`orientation` 也会是 `"vertical"`
- 我们保存的是每个 Dock 的实际尺寸，`resizeDocks()` 会自动处理分割条位置

## 向后兼容性

代码会检查版本：
- **2.0+**: 使用新的 `area_layouts` 字段
- **1.0/1.1**: 回退到旧方法
- **旧格式**: 使用简单恢复

所以你不必担心旧数据丢失！

## 恢复流程

```
1. [150ms] 恢复 Qt 原生状态
2. [300ms] 第一次使用 area_layouts 调整尺寸
3. [200ms] 第二次使用 area_layouts 调整尺寸（巩固）
4. [100ms] 恢复终端 Dock
```

## 查看实际保存的数据

打开你的 `app_config.json`，找到 `dock_layout` → `area_layouts`，你就能看到每个区域的布局信息！

控制台也会打印类似这样的日志：
```
💾 区域 left 布局: 2 个 Dock
💾 Dock 布局已保存: 3 个 Dock, 2 个区域
...
📐 [第1次] 已调整 left 区域 2 个 Dock 的尺寸: [450, 350]
📐 [第2次] 已调整 left 区域 2 个 Dock 的尺寸: [450, 350]
```

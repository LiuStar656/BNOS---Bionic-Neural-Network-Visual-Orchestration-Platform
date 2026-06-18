# 01_node_item 拆分重构

**日期**: 2026-06-18

## 背景

`node_item.py` 是一个 846 行的单体类，承担了节点的全部职责（渲染、交互、配置读写、状态管理、样式管理等 6 大类 18 项功能），是 `ui/canvas/` 模块中行数最大、耦合最深的文件。

## 变更内容

### 拆分后的目录结构

```
ui/canvas/items/
  ├── node_item.py                    (主类：227 行，生命周期 + 委托)
  └── node_components/                (新文件夹，9 个子组件)
       ├── __init__.py                (包导出)
       ├── rendering.py               (paint、自定义颜色)
       ├── subcomponents.py           (文本标签/状态灯/展开按钮构造)
       ├── status_manager.py          (资源监测信号、状态更新、运行时间)
       ├── config_manager.py          (config.json 读写、轮询订阅)
       ├── geometry_handler.py        (itemChange、重叠避免、连线刷新)
       ├── interaction_handler.py     (鼠标事件、锚点连接交互)
       ├── style_manager.py           (样式设置、尺寸、显示更新)
       └── param_panel.py             (详细参数面板构建与销毁)
```

### 架构设计原则

- **组合模式**：主类 `NodeItem` 在 `__init__` 中实例化各子组件，通过 `self._rendering.paint()` 等方式委托
- **对外 API 完全兼容**：所有公共属性/方法的签名保持不变，外部代码无需修改
- **Qt MRO 安全**：避免多重继承导致的 Qt 方法分发问题，改为显式委托
- **重构信息源**：[node_item_refactoring_analysis.md](../../node_item_refactoring_analysis.md)

### 额外修复

- **config_manager.py**: 修复 `_on_external_config_change` 中 `widget.set_value` 未调用（缺少括号和参数）

## 影响范围

- 新增文件：9 个 `node_components/*.py`
- 修改文件：`node_item.py`（从 846 行精简为 227 行）
- 零修改：所有引用 `NodeItem` 的外部文件无需变更

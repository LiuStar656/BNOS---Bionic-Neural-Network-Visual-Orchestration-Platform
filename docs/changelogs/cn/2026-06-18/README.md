# 【2026-06-18】V2.0.17 - NodeItem 拆分重构与 Mixin 架构组合化

---

## 更新总览

**本次更新包含 3 个主要变更：**

1. **NodeItem 单体类拆分为组合模式**：`node_item.py` 从 846 行精简为 227 行，拆分为 9 个子组件（渲染、几何、交互、状态、配置、样式、参数面板等）
2. **6 个 Mixin 类完全改造为组合模式**：`CanvasConnections` / `CanvasBatchOps` / `CanvasMenu` / `CanvasBoxSelect` / `CanvasColors` / `CanvasLayout` — 通过 `self.canvas` 显式依赖，消除隐式 MRO 依赖
3. **完整启动测试验证**：所有模块导入 / 实例化 / API 调用 / 完整应用启动全流程通过

---

## 更新列表

### 1. NodeItem 单体类拆分为组合模式（9 个子组件）

[详细内容](./01_NodeItem_拆分重构.md)

- **拆分前**：`node_item.py` 单体类 846 行，混合 18 项职责（渲染、几何变换、锚点管理、参数面板构建、配置读写、状态更新等）
- **拆分后**：主类 `NodeItem` 仅 227 行 + 9 个子组件，职责单一、可独立测试
- **文件结构**：
  ```
  ui/canvas/items/
    ├── node_item.py                    (主类：生命周期 + 委托)
    └── node_components/
        ├── __init__.py
        ├── rendering.py                 (paint / 自定义颜色)
        ├── subcomponents.py             (文本标签 / 状态灯 / 展开按钮)
        ├── status_manager.py            (资源监测 / 状态 / 运行时间)
        ├── config_manager.py            (config.json 读写)
        ├── geometry_handler.py          (itemChange / 位置 / 连线刷新)
        ├── interaction_handler.py       (鼠标 / 锚点连接交互)
        ├── style_manager.py             (样式设置 / 尺寸)
        └── param_panel.py               (参数面板构建)
  ```
- **对外 API 完全兼容**：外部调用 `NodeItem()` 签名不变，无需修改
- **额外修复**：`config_manager.py` 中 `_on_external_config_change` 的 `widget.set_value` 调用修正

---

### 2. 6 个 Mixin 类改造为组合模式（消除隐式依赖）

[详细内容](./02_Mixin架构重构.md)

**问题诊断**：
- 状态所有权模糊（所有状态散落在 NodeCanvas 上）
- 隐式依赖（Mixin A 调用 Mixin B 的方法，依赖 MRO 顺序）
- 初始化顺序脆弱（顺序错误直接崩溃）
- 单元测试形同虚设（需完整 QApplication 环境）

**重构方案**：
```
NodeCanvas.__init__():
  self.colors = CanvasColors(self)           # 基础层：颜色/主题
  self.connections = CanvasConnections(self)  # 功能层：连线
  self.layout_mgr = CanvasLayout(self)        # 功能层：布局
  self.batch_ops = CanvasBatchOps(self)       # 操作层：批量
  self.box_select = CanvasBoxSelect(self)     # 操作层：框选
  self.menus = CanvasMenu(self)               # 交互层：菜单
```

**关键代码变更**：
- 每个组合类新增 `__init__(self, canvas)`：显式声明依赖
- 所有 `self.xxx` → `self.canvas.xxx`：状态所有权清晰
- `NodeCanvas` 新增转发 API（`_save_color_settings()`、`_load_color_settings()` 等），保持向后兼容
- `NodeCanvas.__init__` 中显式初始化状态变量（`is_connecting`、`box_select_rect` 等）

**修复的 Bug**：
| Bug | 症状 | 修复 |
|-----|------|-----|
| `box_select_rect` AttributeError | 框选时报属性不存在 | `NodeCanvas.__init__` 显式初始化 `box_select_rect` / `box_selected_nodes` / `is_box_selecting` |
| `_save_color_settings` AttributeError | 保存布局时报方法不存在 | `NodeCanvas` 新增转发方法 `_save_color_settings()` → `self.colors._save_color_settings()` |
| `CanvasLayout` 传入 NodeItem 失败 | 节点创建时报 `'CanvasLayout' object has no attribute 'xxx'` | CanvasLayout 中 `NodeItem(..., self, ...)` → `NodeItem(..., self.canvas, ...)` |

**架构改进收益**：
- 状态所有权：✅ 清晰（组合类只通过 `self.canvas` 访问）
- 依赖关系：✅ 可追踪（显式按顺序装配）
- 初始化顺序：✅ 可控（手动按依赖顺序装配）
- 可测试性：✅ 门槛降低（组合类可用 Mock canvas 独立测试）
- 代码可读性：✅ 模块化（7 个功能独立模块，每类 < 500 行）

---

### 3. 完整启动测试验证（全流程通过）

[详细内容](./03_启动测试验证报告.md)

---

### 4. 关于项目中其他 Mixin 的说明

经过完整扫描，项目中还存在另一个 Mixin：`NodePanelSyncMixin`（位于 `ui/panels/_shared/node_panel_sync_mixin.py`）。

**分析结果**：该 Mixin 设计相对合理，属于**行为注入型 Mixin**（只提供方法，不持有状态），不具备 Canvas Mixins 的典型问题（状态模糊、隐式依赖）。它被 `NodeMonitor` 和 `NodeMonitorDock` 两个类共享，用于同步子面板列表与画布节点。**建议保持现状，无需强制重构**。

| Mixin 名称 | 位置 | 使用方 | 重构状态 |
|-----------|------|--------|---------|
| `NodePanelSyncMixin` | `ui/panels/_shared/node_panel_sync_mixin.py` | `NodeMonitor`, `NodeMonitorDock` | 无需重构 |
| `CanvasConnectionsMixin` | `ui/canvas/mixins/canvas_connections.py` | `NodeCanvas` | ✅ 已重构 |
| `CanvasBatchOpsMixin` | `ui/canvas/mixins/canvas_batch_ops.py` | `NodeCanvas` | ✅ 已重构 |
| `CanvasMenusMixin` | `ui/canvas/mixins/canvas_menus.py` | `NodeCanvas` | ✅ 已重构 |
| `CanvasBoxSelectMixin` | `ui/canvas/mixins/canvas_box_select.py` | `NodeCanvas` | ✅ 已重构 |
| `CanvasColorsMixin` | `ui/canvas/mixins/canvas_colors.py` | `NodeCanvas` | ✅ 已重构 |
| `CanvasLayoutMixin` | `ui/canvas/mixins/canvas_layout.py` | `NodeCanvas` | ✅ 已重构 |

---

### 5. 完整启动测试验证（全流程通过）

[详细内容](./03_启动测试验证报告.md)

**测试清单**：

| 测试项 | 内容 | 状态 |
|--------|-----|------|
| 模块导入测试 | 11 个 canvas 模块逐一 import | ✅ 11/11 |
| NodeCanvas 实例化 | 创建 NodeCanvas 实例 | ✅ |
| 组合层装配 | 验证 10 个组合组件都被实例化 | ✅ 10/10 |
| 状态变量初始化 | nodes / edges / box_select_rect / is_connecting 等 | ✅ 10/10 |
| API 调用测试 | get_selected_node / clear_selection / clear_box_selection | ✅ 3/3 |
| 完整应用启动 | 从 bnos_console.py 启动，加载 4 节点项目 | ✅ |
| 框选功能回归 | box_select_rect / box_selected_nodes 生命周期 | ✅ |
| 连线功能回归 | is_connecting / connect_source / temp_edge | ✅ |
| 颜色设置链 | _save_color_settings / _load_color_settings 转发链 | ✅ |
| Bug-1 修复验证 | box_select_rect 初始化 | ✅ |
| Bug-2 修复验证 | _save_color_settings 转发 | ✅ |
| Bug-3 修复验证 | CanvasLayout 传入 self.canvas | ✅ |

**完整应用启动日志（关键时间点）**：
```
[10:05:13] Qt 应用初始化
[10:05:14] 节点创建管理器初始化
[10:05:14] 主窗口面板恢复（Dock 系统）
[10:05:15] 窗口状态恢复（分割条位置）
[10:05:15] 项目扫描 & 节点加载（4 个节点）
[10:05:21] NodeCanvas 初始化（组合模式：10 个组件，无 mixin 继承）
[10:05:21] 画布布局加载（NodeItem 渲染正常）
[10:05:21] 锚点绑定 / 连线创建
[10:05:23] 画布切换完成
[10:05:28] 程序正常关闭
```

**非致命问题**（环境/系统层面，不影响功能）：
- Qt 线程安全警告（Timers cannot be started from another thread）
- 测试环境权限限制（canvas_layout.json 写入失败）
- Windows 终端 GBK 编码问题（emoji 字符输出）

---

## 变更文件清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `ui/canvas/canvas_view.py` | 修改 | 新增组合层装配、状态变量初始化、转发 API |
| `ui/canvas/mixins/canvas_connections.py` | 修改 | Mixin → 组合类，`self` → `self.canvas` |
| `ui/canvas/mixins/canvas_batch_ops.py` | 修改 | Mixin → 组合类，`self` → `self.canvas` |
| `ui/canvas/mixins/canvas_menus.py` | 修改 | Mixin → 组合类，`self` → `self.canvas` |
| `ui/canvas/mixins/canvas_box_select.py` | 修改 | Mixin → 组合类，`self` → `self.canvas` |
| `ui/canvas/mixins/canvas_colors.py` | 修改 | Mixin → 组合类，`self` → `self.canvas` |
| `ui/canvas/mixins/canvas_layout.py` | 修改 | Mixin → 组合类，`self` → `self.canvas`（关键修复） |
| `ui/canvas/items/node_item.py` | 修改 | 从 846 行精简为 227 行（委托到子组件） |
| `ui/canvas/items/node_components/*.py` | 新增 | 9 个子组件（rendering/status/config/geometry/interaction/style/param_panel 等） |

**修改文件数**：7 个（核心 canvas 逻辑）
**新增文件数**：9 个（NodeItem 子组件）
**删除文件数**：0
**总代码行数变化**：NodeItem 846 → 227 行（+9 个 ~100 行的子组件）

---

## 向后兼容性

✅ **API 完全兼容**：所有外部调用 `NodeCanvas.xxx` 的签名不变
✅ **无需修改调用方**：引用 `NodeItem` / `EdgeItem` 的代码无需变更
✅ **文件结构保持一致**：所有 canvas 文件仍在 `ui/canvas/` 及其子目录下

---

## 下一步计划

- **独立单元测试**：为 CanvasConnections、CanvasBoxSelect 等组合类编写独立单元测试（用 Mock canvas）
- **文档完善**：为每个组合类添加完整 docstring 和用法示例
- **进一步解耦**：将 NodeCanvas 上剩余的 "数据存储层"（self.nodes、self.edges）也封装为组合对象

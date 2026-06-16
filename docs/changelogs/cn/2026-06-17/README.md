# 【2026-06-17】V2.0.16 - 画布布局加载修复、自动打开项目异步化、节点增删持久化与 Canvas 模块目录重构

---

## 更新总览

**本次更新解决 4 个核心问题 + 1 项结构性重构**：
1. **首次打开软件画布节点不显示**：时序问题导致 `load_layout()` 在 `nodes_data` 填充前执行
2. **节点从节点列表面板拖入/移除画布不保存**：`add_node_to_canvas` 和 `remove_node_from_canvas` 未触发自动保存
3. **空引用崩溃**：`_terminal_dock` 未初始化即被访问、`NodeListDockPanel` 缺少 `refresh()` 方法
4. **Canvas 模块目录重构**：`ui/canvas/` 根目录堆积的 13 个 Python 文件按职责拆分为 `mixins/` 与 `drawing/` 两个子目录，并保留旧路径兼容代理

---

## 更新列表

### 1. 画布布局加载修复（try/finally + scene/viewport 强制刷新）

[详细内容](./01_画布布局加载修复.md)

- **`load_layout` 生命周期保护**：用 `try/finally` 包裹 `setUpdatesEnabled(False)`，无论是否抛异常都保证 `setUpdatesEnabled(True)` 被调用
- **Scene/Viewport 强制刷新**：`finally` 块中新增 `self.scene.update(self.scene.sceneRect())` 和 `self.viewport().update()`，确保新增节点/连线立即渲染
- **详细诊断日志**：加载完成后输出节点数量、位置、尺寸、可见性、Z 值，便于排查渲染层问题
- **逻辑修正**：移除从 `nodes_data` 自动创建画布节点的逻辑（画布节点只应来自 `canvas_layout.json`，项目节点在节点列表面板显示）

---

### 2. 自动打开项目异步化重构（与 project_open 统一时序）

[详细内容](./02_自动打开项目异步化重构.md)

- **根因诊断**：之前 `_auto_open_project` 调用 `project_refresh(async_mode=False)` 后**立即**创建画布，但 Worker 在后台异步扫描磁盘 → `nodes_data` 还是空的 → `canvas_layout.json` 读取到空节点列表
- **异步化重构**：改为与 `project_open` 完全相同的 `ProjectLoadWorker` 模式 — Worker 后台扫描 → `finished` 信号回到主线程 → 填充 `nodes_data` → 创建画布 → `load_layout` → 恢复状态
- **新方法 `remove_canvas_dock_by_path`**：`CanvasHost` 新增按项目路径清理画布 dock，防止同一项目重复打开时 dock 残留
- **正确调用链**：`Worker.scan → nodes_data 填充 → add_canvas_dock → load_layout → restore_state`

---

### 3. 节点增删自动保存触发（避免手动拖入节点后重启丢失）

[详细内容](./03_节点增删自动保存触发.md)

- **`add_node_to_canvas` 扩展**：新增可选参数 `node_info`（子进程模式下直接传入节点信息），解决 `canvas_process.py` 中 `add_node_to_canvas(node_name, info)` 参数不匹配导致的 `TypeError`
- **保存触发器**：节点添加到画布后执行 `_save_timer.stop()` / `_save_timer.start(500)`，触发防抖自动保存到 `canvas_layout.json`
- **节点移除保存**：`remove_node_from_canvas` 同样在完成后触发 `_save_timer` 防抖保存
- **操作日志**：添加/移除节点时输出操作日志，便于追踪画布变更

---

### 4. 终端 Dock 与节点面板空引用修复（AttributeError 全消除）

[详细内容](./04_终端与节点面板空引用修复.md)

- **`_terminal_dock` 未初始化保护**：`_update_terminal_on_canvas_change` 先检查 `hasattr(self, '_terminal_dock')`，未初始化（第一个画布创建前）直接返回
- **`NodeListDockPanel.refresh()` 新增**：便捷方法从 `self.parent_window.nodes_data` 重新加载节点列表，使 `_auto_open_project` 后的面板刷新正常工作
- **双重安全保护**：`state.py` 中对 `node_list_panel` 的调用先做 `hasattr` 检查，再调用存在的方法

---

### 5. Canvas 模块目录重构（组合层 + mixins + drawing 三目录）

[详细内容](./05_canvas目录结构重构_组合层与子目录化.md)

- **重构前**：`ui/canvas/` 根目录堆积 13 个 Python 文件（入口类、7 个 Mixin、4 个组合层、controllers、绘图层等）
- **重构后**：
  - 根目录仅保留 `canvas_view.py`（NodeCanvas 主类）、`canvas_process.py`（子进程入口）、`__init__.py`
  - 新增 `ui/canvas/mixins/` — 收纳 `canvas_connections`、`canvas_box_select`、`canvas_batch_ops`、`canvas_menus`、`canvas_layout`、`canvas_colors`、`canvas_selection`、`canvas_background_renderer`、`canvas_node_manager`、`canvas_event_handlers`、`controllers` 共 11 个逻辑模块
  - 新增 `ui/canvas/drawing/` — 收纳 `draw_layer`、`draw_toolbar`、`graphic_items/` 绘图基元集合
- **向后兼容代理（关键）**：在 `ui/canvas/__init__.py` 中通过 `sys.modules.setdefault(alias, real_module)` 注入别名，使得 `from ui.canvas.canvas_layout import ...`、`from ui.canvas.draw_layer import ...` 等旧路径**继续生效**，且 `mod_old is mod_new`（新旧路径模块对象相同，无"同文件 import 两次"问题）
- **业务代码零变更**：文件仅是物理迁移 + import 路径重写 + 在 `__init__.py` 中注入兼容层；未改动任何业务逻辑

---

## 主要更新

| 类别 | 更新内容 |
|------|----------|
| **画布加载** | `load_layout` try/finally 保护；scene/viewport 强制刷新；详细诊断日志；只从 `canvas_layout.json` 恢复节点 |
| **异步化** | `_auto_open_project` 改为 `ProjectLoadWorker` Signal 模式；`CanvasHost.remove_canvas_dock_by_path()` 新增 |
| **持久化** | `add_node_to_canvas` / `remove_node_from_canvas` 后触发 `_save_timer.start(500)` 防抖保存 |
| **Bug 修复** | `CanvasHost._terminal_dock` 未初始化保护；`NodeListDockPanel` 缺少 `refresh()` 方法；`add_node_to_canvas` 参数不匹配 |
| **目录结构** | `ui/canvas/` 根目录从 13 个 Python 文件精简到 3 个；新增 `mixins/`（11 个逻辑模块）与 `drawing/`（绘图层 + graphic_items）；`__init__.py` sys.modules 别名代理保持旧路径向后兼容 |
| **代码质量** | 所有修改文件 `ast.parse` 语法验证通过；无新增 `AttributeError`；0 处业务逻辑变更（重构项） |

---

## 修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `ui/canvas/canvas_layout.py` | `load_layout` 增加 try/finally；scene/viewport 强制刷新；诊断日志；移除 nodes_data 自动创建逻辑 |
| `ui/core/canvas_host.py` | `_remove_blank_placeholder` 增加透明中央占位控件；画布 dock 显式显示；新增 `remove_canvas_dock_by_path`；`_update_terminal_on_canvas_change` 空引用保护 |
| `ui/main_window/state.py` | `_auto_open_project` 完全重构为 `ProjectLoadWorker` 异步模式；`node_list_panel.refresh()` 改用 `update_node_list()` |
| `ui/canvas/canvas_view.py` | `add_node_to_canvas` 接受可选 `node_info` 参数；节点增删后触发 `_save_timer` 保存；import 路径指向新的 mixins/drawing 子目录 |
| `ui/panels/node_list_dock.py` | 新增 `refresh()` 便捷方法 |
| `ui/canvas/__init__.py` | 新增 `sys.modules` 别名代理（`ui.canvas.canvas_layout → ui.canvas.mixins.canvas_layout` 等 13 项映射） |
| `ui/canvas/mixins/`（11 文件） | 新建目录，从根目录移动而来，内容无逻辑变更 |
| `ui/canvas/drawing/`（3 文件 + graphic_items/） | 新建目录，从根目录移动而来，内容无逻辑变更 |

---

## 验证结果

- ✅ 5 个修改文件 `ast.parse` 语法验证全部通过
- ✅ 启动时自动打开项目：画布节点正确显示（不再为空）
- ✅ 手动从节点列表拖入节点到画布：500ms 后 `canvas_layout.json` 自动更新
- ✅ 从画布移除节点：`canvas_layout.json` 同步更新，重启后节点不在画布上，只在列表面板显示
- ✅ `_terminal_dock` 空引用：不再出现 `AttributeError`
- ✅ `NodeListDockPanel.refresh()` 调用：正常执行，节点列表从 `nodes_data` 重新渲染
- ✅ 同时打开多个项目：切换时画布节点正确加载
- ✅ 关闭时无 `QProcess: Destroyed while process is still running` 新增错误（现有警告为历史遗留，后续单独处理）
- ✅ **Canvas 目录重构验证**：`from ui.canvas.canvas_layout import ...` / `from ui.canvas.draw_layer import ...` 等旧路径导入仍生效；`import ui.canvas.canvas_layout as mod_old; import ui.canvas.mixins.canvas_layout as mod_new; assert mod_old is mod_new` 通过；新路径 `from ui.canvas.mixins.canvas_connections import ...` / `from ui.canvas.drawing.graphic_items import ...` 全部正常；启动应用无 ImportError

# 2026-07-13 更新总览

[返回总索引](../README.md)

---

## 更新目录

- [01 复合节点右键菜单优化与输入锚点独占检测](#01-复合节点右键菜单优化与输入锚点独占检测)
- [02 复合节点折叠 DAG 拓扑更新修复](#02-复合节点折叠dag拓扑更新修复)
- [03 复合节点展开坐标与连线修复](#03-复合节点展开坐标与连线修复)
- [04 节点运行态保护](./04_节点运行态保护.md)
- [05 复合节点 UI 重构与自定义接口支持](./05_复合节点UI重构与自定义接口支持.md)
- [06 复合节点启动队列集成](./06_复合节点启动队列集成.md)
- [07 复合节点重命名功能](./07_复合节点重命名功能.md)
- [08 锚点管理器多输出端口支持](./08_锚点管理器多输出端口支持.md)
- [09 DAG 运行状态追踪](./09_DAG运行状态追踪.md)
- [10 节点多选功能修复](./10_节点多选功能修复.md)
- [11 复合节点启动队列集成修复](./11_复合节点启动队列集成修复.md)
- [12 多选右键菜单优化与复合节点支持](./12_多选右键菜单优化与复合节点支持.md)
- [13 节点详情面板合并与复合节点配置窗口修复](./13_节点详情面板合并与复合节点配置窗口修复.md)
- [14 README 重写与归档](./14_README重写与归档.md)
- [15 状态机系统](./15_状态机系统.md)
- [16 节点运行时状态机集成](./16_节点运行时状态机集成.md)
- [17 复合节点生命周期状态机集成](./17_复合节点生命周期状态机集成.md)
- [18 启动队列僵尸条目修复](./18_启动队列僵尸条目修复.md)

---

## 01 复合节点右键菜单优化与输入锚点独占检测

详见 [01_复合节点右键菜单优化与输入锚点独占检测.md](./01_复合节点右键菜单优化与输入锚点独占检测.md)。

### 摘要

- **右键菜单启动/停止互斥**：根据 `is_running()` 只显示其中一个，不再同时出现
- **解耦移至最底层**：运行时灰显 + tooltip 提示
- **展开/折叠运行时检查**：运行时灰显 + tooltip，点击额外弹窗校验
- **输入锚点独占检测**：一个输入锚点只能连接一个输出锚点，连线时检测 `target_anchor.edges` 拒绝重复接入

---

## 02 复合节点折叠 DAG 拓扑更新修复

详见 [02_复合节点折叠DAG拓扑更新修复.md](./02_复合节点折叠DAG拓扑更新修复.md)。

### 摘要

- **根因**：折叠时 `internal_edge_info` 只写入内存 `comp["_internal_edges"]`，`composite.json` edges 从未更新，导致 `pipeline.json` 使用旧拓扑
- **修复**：折叠时立即同步 edges 到 `composite.json`（`src→from / tgt→to` 格式映射），`_sync_pipeline` 改为无条件执行
- **效果**：展开后重新编排子节点顺序再折叠，DAG 拓扑正确生效（如先 +1 再 ×3 vs 先 ×3 再 +1）

---

## 03 复合节点展开坐标与连线修复

详见 [03_复合节点展开坐标与连线修复.md](./03_复合节点展开坐标与连线修复.md)。

### 摘要

- **坐标偏移修复**：展开时使用复合节点当前位置 `comp_item.pos()` 而非保存的旧 `canvas_position`
- **端口名称映射**：添加 `"data"` → `"default"` 映射，解决默认输入锚点与端口识别名称不匹配问题
- **布局保存/加载过滤**：跳过折叠复合节点的子节点，避免加载旧坐标导致偏移
- **执行顺序调整**：先定位子节点再创建连线，确保边端点使用正确位置

---

## 04 节点运行态保护

### 摘要

- **重命名保护**：运行中的节点禁止重命名，弹出 toast 提示
- **删除保护**：删除包含运行中节点时，弹出确认对话框提示用户

### 修改文件

| 文件 | 改动 |
|------|------|
| `ui/panels/node_list_panel.py` | 重命名前检测运行状态；删除前检测运行中节点并弹窗确认 |
| `ui/core/node/node_process.py` | 新增 `check_node_not_running()` 通用检测函数 |

---

## 05 复合节点 UI 重构与自定义接口支持

### 摘要

- **复用普通节点组件**：使用 `NodeRendering`、`AnchorManager`、`NodeSubComponents`、`NodeParamPanel` 实现一致的 UI
- **隐藏冗余元素**：隐藏 IN/OUT 标签、展开按钮，保留状态指示器
- **过滤系统端口**：过滤系统生成的端口（如 `_out` 后缀），只显示自定义端口
- **修复缺失属性**：显式调用 `build_text_labels()` 创建 `name_text` 属性
- **添加复合节点标记**：左上角绿色圆点标识

### 修改文件

| 文件 | 改动 |
|------|------|
| `ui/canvas/items/composite_node_item.py` | 重构为复用普通节点组件；隐藏冗余元素；添加绿色圆点标记 |

---

## 06 复合节点启动队列集成

### 摘要

- **启动队列支持**：复合节点现在能像普通节点一样进入启动队列
- **自动判断类型**：`NodeStartWorker.run()` 根据节点名前缀 `composite_` 自动选择启动方式
- **新增启动方法**：`_start_composite()` 通过 `CompositeNodeManager` 启动复合节点

### 修改文件

| 文件 | 改动 |
|------|------|
| `ui/core/node/node_startup_queue.py` | 新增 `_start_composite()` 方法；`run()` 方法自动判断节点类型 |

---

## 07 复合节点重命名功能

### 摘要

- **节点列表右键菜单**：新增「重命名复合节点」选项
- **运行态保护**：运行中的复合节点禁止重命名
- **展示名称编辑**：通过输入框编辑 `display_name`，留空恢复 hex ID 显示

### 修改文件

| 文件 | 改动 |
|------|------|
| `ui/panels/node_list_context.py` | 新增 `_rename_composite_group()` 方法；右键菜单添加重命名选项 |

---

## 08 锚点管理器多输出端口支持

### 摘要

- **多输出端口模式**：优先使用 `output_ports` 配置的多输出端口
- **位置计算**：优先使用 `row_positions` 中的位置，否则垂直分布
- **回退机制**：无多输出配置时回退到单个 default 输出锚点

### 修改文件

| 文件 | 改动 |
|------|------|
| `ui/canvas/items/anchor_manager.py` | 重写输出锚点生成逻辑，支持多输出端口 |

---

## 09 DAG 运行状态追踪

### 摘要

- **节点级状态追踪**：`DagRunner` 记录每个子节点的执行状态（ok/fail/pending）、错误信息、耗时
- **状态持久化**：执行完成后写入 `status.json`，供 BNOS 监控
- **并行执行追踪**：并行节点的失败状态也会被记录

### 修改文件

| 文件 | 改动 |
|------|------|
| `ui/core/node/composite_orchestrator.py` | 新增 `_node_status` 追踪；新增 `_write_status()` 方法 |

---

## 10 节点多选功能修复

详见 [10_节点多选功能修复.md](./10_节点多选功能修复.md)。

### 摘要

- **根本原因**：Qt 的 `QGraphicsScene` 默认选择模式是 `SingleSelection`，调用 `setSelected(True)` 会自动取消其他节点的选中状态
- **修复方案**：使用自定义选中标志 `_is_custom_selected` 完全绕过 Qt 的选择模式
- **修改文件**：`rendering.py`、`canvas_selection.py`、`canvas_view.py`、`selection_tool.py`

---

## 11 复合节点启动队列集成修复

详见 [11_复合节点启动队列集成修复.md](./11_复合节点启动队列集成修复.md)。

### 摘要

- **根本原因**：`_composite_start` 直接调用 `mgr.start_inprocess()`，没有经过启动队列
- **修复方案**：改为通过启动队列启动，并显示启动提示；修改 `start_selected_node_by_name` 和 `stop_selected_node_by_name` 支持复合节点
- **修改文件**：`canvas_menus.py`、`node_list_context.py`、`main_window/node.py`、`composite_node_item.py`

---

## 12 多选右键菜单优化与复合节点支持

详见 [12_多选右键菜单优化与复合节点支持.md](./12_多选右键菜单优化与复合节点支持.md)。

### 摘要

- **选中数量统计**：修复 `SelectedNodesList._sync` 不包含复合节点的问题
- **菜单选项动态调整**：包含复合节点时隐藏"批量移除"和"压缩为复合节点"选项
- **启动/停止支持**：修改 `start_selected_node_by_name` 和 `stop_selected_node_by_name` 支持复合节点
- **新增菜单选项**：清除选择

---

## 13 节点详情面板合并与复合节点配置窗口修复

详见 [13_节点详情面板合并与复合节点配置窗口修复.md](./13_节点详情面板合并与复合节点配置窗口修复.md)。

### 摘要

- **窗口合并**：将"展开节点"和"节点配置"窗口合并为统一的节点详情面板
- **复合节点配置窗口修复**：修复缩进错误和项目路径属性名错误，使配置窗口正常显示
- **复合节点重启后展开修复**：`save_layout` 保存所有节点（包括内部节点）并标记 `is_internal`；`load_layout` 恢复内部节点并保持隐藏
- **防错保护**：启动/停止按钮添加 `_operation_in_progress` 防并发标志
- **国际化支持**：添加节点详情面板翻译键和翻译文本
- **菜单优化**：移除普通节点右键菜单中的重复"展开节点"选项

---

## 14 README 重写与归档

详见 [14_README重写与归档.md](./14_README重写与归档.md)。

### 摘要

- **README 重写（中英文）**：~1100 行 → ~220 行，9 章节结构，突出核心设计理念与架构层级
- **复合节点系统专题**：新增独立章节，覆盖 DAG 压缩/展开折叠/编排器/端口路由/双模式运行时
- **修正过时引用**：`bnos_gui.py` → `launcher.py` / `bnos_console.py`，`requirements_gui.txt` → 实际依赖
- **架构图重绘**：双层启动 → ApplicationContext → 核心服务 → 节点系统的层级关系
- **大幅精简**：删除 BNOS vs Low-Code 长表、删除详细操作指南，保留 5 步快速上手
- **旧版归档**：`docs/archived/README_v1_archived.md` / `README_CN_v1_archived.md`（含归档标记）
- **更新 changelogs**：新增 CN/EN changelog 条目，更新日期索引、总索引、INDEX 全部索引文件

---

## 15 状态机系统

详见 [15_状态机系统.md](./15_状态机系统.md)。

### 摘要

- **状态机基类**：基于 QObject + Signal，Transition 数据类支持 guard/action/wildcard
- **Phase 1 NodeRuntimeSM**：6 状态 14 转换，统一 3 套矛盾的状态值
- **Phase 2 CompositeLifecycleSM**：8 状态 15 转换，is_active/is_restartable 属性
- **Phase 3 CanvasModeSM**：6 模式 14 转换，互斥规则（CONNECTING ↔ PANNING）
- **Phase 4 EdgeInteractionSM**：6 状态 8 转换，is_interacting 属性
- **测试**：5 文件 52 项测试全部通过
- **位置**：`ui/core/state/` 独立包，零业务依赖

---

## 16 节点运行时状态机集成

详见 [16_节点运行时状态机集成.md](./16_节点运行时状态机集成.md)。

### 摘要

- **桥接层**：`node_runtime_bridge.py` 提供 `ensure_sm` / `transition_state` / `get_state` 兼容 `node_info["status"]`
- **start_node_process**：SM 启动守卫（非法状态直接拒绝）+ start/start_ok/start_fail 转换
- **stop_node_process**：SM 停止守卫 + stop/stop_ok/stop_fail 转换
- **check_running_processes**：child_resume/child_idle/crash SM 事件 + 僵尸进程处理
- **detect_running_nodes**：统一 `get_state` 读取

---

## 17 复合节点生命周期状态机集成

详见 [17_复合节点生命周期状态机集成.md](./17_复合节点生命周期状态机集成.md)。

### 摘要

- **start_inprocess**：TOCTOU `is_restartable` 守卫；异常路径资源泄漏修复（日志文件句柄清理）
- **stop_composite**：`is_active` 守卫 + stop_ok/stop_fail 转换
- **decompress**：decompress/remove_done 生命周期转换 + SM 清理
- **is_running**：委托生命周期 SM（`is_active`），含 Popen 兜底

---

## 18 启动队列僵尸条目修复

详见 [18_启动队列僵尸条目修复.md](./18_启动队列僵尸条目修复.md)。

### 摘要

- **根因**：`_on_node_start_complete` 成功后未从 `self._queue` 移除条目，`enqueue` 误判重复
- **修复**：SUCCESS/FAILED 后调用 `_remove_from_queue` 清理
- **防御**：`enqueue` 重复检查只考虑非终态（排除 SUCCESS/FAILED/CANCELLED）
- **效果**：复合节点停止后可正常再次启动

---

## 修改文件清单

| 文件 | 改动 |
|------|------|
| `ui/canvas/mixins/canvas_menus.py` | 重写 `_show_composite_node_menu`；新增 `_on_toggle_expand`；`_composite_start` 通过启动队列；`_show_multi_node_menu` 动态调整菜单；移除普通节点右键菜单重复选项 |
| `ui/canvas/mixins/canvas_connections.py` | `create_edge` 新增输入锚点独占检测 |
| `ui/core/node/composite_node.py` | `_collapse_composite` 新增 DAG 拓扑同步逻辑；展开坐标修复；端口名称映射；执行顺序调整；展开时容错处理缺失节点 |
| `ui/canvas/mixins/canvas_layout.py` | 保存/加载布局时包含内部节点并标记 `is_internal`；内部节点加载后保持隐藏 |
| `ui/panels/node_list_panel.py` | 重命名/删除运行态保护 |
| `ui/core/node/node_process.py` | 新增 `check_node_not_running()` |
| `ui/canvas/items/composite_node_item.py` | UI 重构，复用普通节点组件；新增 `update_status` 方法 |
| `ui/core/node/node_startup_queue.py` | 复合节点启动队列集成；新增 `_start_composite()` |
| `ui/panels/node_list_context.py` | 复合节点重命名功能；`_start_composite_group` 通过启动队列 |
| `ui/canvas/items/anchor_manager.py` | 多输出端口支持 |
| `ui/core/node/composite_orchestrator.py` | DAG 运行状态追踪 |
| `ui/core/node/node_config_parser.py` | 输入端口名称校验 |
| `ui/canvas/items/node_components/rendering.py` | 使用自定义选中标志 |
| `ui/canvas/mixins/canvas_selection.py` | 多选逻辑使用自定义选中标志 |
| `ui/canvas/canvas_view.py` | `SelectedNodesList` 同步自定义选中状态；包含复合节点 |
| `ui/canvas/drawing/tools/selection_tool.py` | 空白点击清除自定义选中状态 |
| `ui/main_window/node.py` | `start_selected_node_by_name` 和 `stop_selected_node_by_name` 支持复合节点 |
| `ui/dialogs/node_detail_panel.py` | 合并窗口；修复缩进错误；添加异常捕获 |
| `ui/dialogs/node_data_provider.py` | 修复项目路径属性名；新增 CompositeNodeProvider |
| `ui/dialogs/json_sync_editor.py` | 新增：双向同步 JSON 编辑器 |
| `ui/dialogs/log_viewer_widget.py` | 新增：日志查看器组件 |
| `ui/dialogs/node_control_widget.py` | 新增：节点控制组件（含防错保护） |
| `ui/canvas/mixins/canvas_node_manager.py` | 删除节点时同步更新复合节点 |
| `ui/core/i18n/strings_cn.json` | 新增节点详情面板翻译 |
| `ui/core/i18n/strings_en.json` | 新增节点详情面板翻译 |
| `ui/core/i18n/translation_keys.py` | 新增翻译键常量 |

| `README.md` | 重写：~1100 行 → ~220 行，9 章节结构 |
| `README_CN.md` | 重写：~1100 行 → ~220 行，9 章节结构 |
| `docs/archived/README_v1_archived.md` | 新增：旧版英文 README 归档（含归档标记） |
| `docs/archived/README_CN_v1_archived.md` | 新增：旧版中文 README 归档（含归档标记） |
| `docs/changelogs/cn/2026-07-13/14_README重写与归档.md` | 新增：本 changelog |
| `docs/changelogs/en/2026-07-13/14_README_Rewrite_and_Archive.md` | 新增：英文 changelog |
| `docs/changelogs/cn/2026-07-13/README.md` | 更新：日期索引新增条目 14 |
| `docs/changelogs/en/2026-07-13/README.md` | 更新：日期索引新增条目 14 |
| `docs/changelogs/cn/README.md` | 更新：总索引 details 折叠新增条目 |
| `docs/changelogs/en/README.md` | 更新：总索引 details 折叠新增条目 |
| `docs/changelogs/cn/INDEX.md` | 更新：日期索引新增条目 |

| `ui/core/state/__init__.py` | 新增：导出 StateMachine, Transition |
| `ui/core/state/base.py` | 新增：状态机基类 |
| `ui/core/state/node_runtime.py` | 新增：NodeRuntimeSM |
| `ui/core/state/composite_lifecycle.py` | 新增：CompositeLifecycleSM |
| `ui/core/state/canvas_mode.py` | 新增：CanvasModeSM |
| `ui/core/state/edge_interaction.py` | 新增：EdgeInteractionSM |
| `ui/core/state/node_runtime_bridge.py` | 新增：桥接兼容层 |
| `ui/core/state/tests/test_base.py` | 新增：11 项测试 |
| `ui/core/state/tests/test_node_runtime.py` | 新增：13 项测试 |
| `ui/core/state/tests/test_composite_lifecycle.py` | 新增：10 项测试 |
| `ui/core/state/tests/test_canvas_mode.py` | 新增：10 项测试 |
| `ui/core/state/tests/test_edge_interaction.py` | 新增：8 项测试 |
| `ui/core/node/node_startup_queue.py` | `_remove_from_queue` 清理终态条目；`enqueue` 防御性加固 |
| `docs/changelogs/en/INDEX.md` | 更新：日期索引新增条目 |

---

**最后更新**：2026-07-13

# 2026-07-15 更新总览

[返回总索引](../README.md)

---

## 更新目录

- [01 复合节点虚线修复与端口别名规范化](#01-复合节点虚线修复与端口别名规范化)
- [02 MUTEX-VIOLATION 互斥断言时序修复](#02-mutex-violation-互斥断言时序修复)
- [03 日志降噪与稳态日志分级](#03-日志降噪与稳态日志分级)
- [04 状态机系统开发阶段盘点（节点线 + 边线条）](#04-状态机系统开发阶段盘点节点线--边线条)
- [05 节点选择双源同步修复与复合节点双击配置页面](#05-节点选择双源同步修复与复合节点双击配置页面)

---

## 01 复合节点虚线修复与端口别名规范化

详见 [01_复合节点虚线修复与端口别名规范化.md](./01_复合节点虚线修复与端口别名规范化.md)。

### 摘要

- **composite.json 读取路径修正**：移除 canonical_edge_resolver.py 中冗余的 `NODE_DIR_ROOT` 拼接层（`nodes/composite_nodes` → `composite_nodes`），让 COMPOSITE_INPUT/OUTPUT/INTERNAL 三类权威边正确加载
- **权威集别名扩展**：解析 composite.json 外部连接时，输入端口 `{data, default}`、输出端口 `{node_output, default}` 两种 EdgeKey 版本都加入 CanonicalEdgeSet，兼容历史布局
- **NodeStateManager 别名等价比较**：`is_edge_valid_static` 中对复合边增加 data↔default / node_output↔default 端口别名等价判定
- **路由写入统一规范化**：`set_input_routing` / `set_output_routing` 入口强制标准化到内部标准名（输入 data、输出 node_output），写入后反删别名脏键，解决 composite.json 同时写 data+default 重复条目
- **路由清理别名宽松匹配**：`clear_input_routing` / `clear_output_routing` 传入任一端口别名都能正确清理标准名+别名键

---

## 02 MUTEX-VIOLATION 互斥断言时序修复

详见 [02_Mutex断言时序修复.md](./02_Mutex断言时序修复.md)。

### 摘要

- **根因**：旧时序 ASSERT(读磁盘) → FLUSH(写磁盘)，断言在 RouteCache 原子写盘前执行，读到 PhaseB CLEAR 之后、PhaseC 新值尚未刷出的磁盘瞬态 → 假阳性 MUTEX-VIOLATION + 误回滚
- **修复**：expand/collapse 都改为 `PhaseB CLEAR → PhaseC CREATE → [PhaseD RouteCache.flush] → _assert_mutex_consistency` 顺序，断言读到的就是最新写盘值
- **断言失败策略调整**：flush 已写盘后不再回滚（rollback 只能回滚内存，磁盘不一致反而更糟），只保留 ERROR 级别日志记录
- **影响**：连续 expand/collapse 不再抛 AssertionError；即使真实不一致（用户手动改坏）也不误回滚数据

---

## 03 日志降噪与稳态日志分级

详见 [03_日志降噪与稳态日志分级.md](./03_日志降噪与稳态日志分级.md)。

### 摘要

- **兜底扫描周期**：`CANONICAL_SCAN_INTERVAL_MS` 3000ms → 10000ms（expand/collapse/load_layout/calibrate 都会立即 trigger immediate scan，不依赖定时器）
- **Render-Gate 分级**：noisy = ghost_edges > 0 ∨ broken_paths > 0 ∨ 集合大小变化；noisy=True → INFO 级完整 summary + canonical/canvas set dump；noisy=False（稳态 idle）→ 仅一行 DEBUG summary，默认不输出
- **infer_all_edges 分级**：need_attention = broken_paths > 0 ∨ stale_routes_cleared > 0；True→INFO，False→DEBUG
- **ScanStats 字段名修正**：`stats.stale_cleared` → `stats.stale_routes_cleared`，消除 AttributeError
- **效果**：闲置状态下日志量 ≈ 0；用户操作后 1 轮完整输出；异常（ghost/broken/stale）保留完整 INFO dump

---

## 04 状态机系统开发阶段盘点（节点线 + 边线条）

详见 [04_状态机系统开发阶段盘点.md](./04_状态机系统开发阶段盘点.md)。

### 摘要

- **节点线（Node Track）成熟度**：Phase 1 NodeRuntimeSM ✅ 100%（node_process.py 10 处真实 transition_state 调用）；Phase 3 CompositeLifecycleSM ✅ 100%（composite_node.py 4 处真实接入 + is_active/is_restartable 属性委托）；Phase 2 正交 SM 组合 + TRANSITION_TABLE + Guard 🟡 ~60%（NodeStateManager 多处实例化 + 事件分发入口已接 8 个事件，但 NodeStateActionService 动作层仍走老路径）；Render-Gate 接口 ✅ 100%（canvas_edge_render_gate.py 真实调用 is_edge_valid_static）；RouteCache ✅ 100%（expand/collapse 全链路）
- **边线条（Edge Track）成熟度**：Phase 4 EdgeInteractionSM 🟠 定义/单测 100% 但业务 0% 接入（edge_item.py 仍保留旧 8 个布尔状态变量操作，EdgeInteractionSM 未实例化）；CanvasModeSM 🟠 定义/单测 100% 但业务 0% 接入（画布模式仍用裸字符串）
- **代码树**：ui/core/state 独立包 15 模块 + 7 个测试文件（base / NodeRuntime / CompositeLifecycle / CanvasMode / EdgeInteraction ×1 + phase2_state_manager ×1）
- **下一步路线图 P0→P3**：P0 EdgeInteractionSM→edge_item.py 接入；P1 CanvasModeSM→canvas_view 接入；P2 NodeStateActionService 挂全；P3 启动自检 validate_all_states

---

---

## 05 节点选择双源同步修复与复合节点双击配置页面

详见 [05_节点选择双源同步与复合节点双击配置.md](./05_节点选择双源同步与复合节点双击配置.md)。

### 摘要

- **双源同步根因**：渲染层 `is_selected = _is_custom_selected OR isSelected()` 依赖「自定义标志 OR Qt 原生选择」，但 SelectionManager / SelectedNodesList / CanvasBoxSelect 共 5 处写入口只操作双源中的一个，残留 `False OR True ≡ True` 导致旧节点高亮不消
- **全链路双写修复**：`SelectionManager.on_node_selected` 清除旧节点时 `_is_custom_selected=False + setSelected(False)` 双写并追加 `scene.clearSelection()` 兜底；`_toggle_node_selection` 切换时双源判定同步双写
- **API 写入一致性**：`SelectedNodesList.append/remove/clear` 三个写操作加入 `setSelected()` 同步；`CanvasBoxSelect.clear_box_selection` 加入 `_is_custom_selected=False + update()` 刷新
- **CompositeNodeItem 交互补齐**：新增 `mousePressEvent`（普通单击单选 / Ctrl+单击多选 / 右键菜单 / 连线锚点命中，共 4 条完整语义路径）；新增 `mouseDoubleClickEvent`（调用 `canvas.open_node_config(comp_id)` 打开复合节点配置面板，try/except 异常捕获 + 成功/警告日志）
- **配置面板兼容性验证**：`NodeDetailPanel.create_for_node` 已有双 Provider 架构，`composite_` 前缀自动路由到 `CompositeNodeProvider`（3 Tab：概览 / 集群配置 / 复合结构），前次对话已移除重复的「复合配置」Tab 避免 composite.json 重复打开

---

## 修改文件清单

| 文件 | 改动 |
|------|------|
| `ui/core/edge/canonical_edge_resolver.py` | 去掉 composite.json 读取路径中冗余的 `NODE_DIR_ROOT`；复合边加入端口别名扩展；`infer_all_edges` 日志分级；修正 `stale_cleared` → `stale_routes_cleared` 字段名 |
| `ui/core/state/node_state_manager.py` | `is_edge_valid_static` 增加复合边 data↔default / node_output↔default 别名端口等价比较 |
| `ui/canvas/mixins/canvas_connections.py` | `create_edge` 创建复合节点边时使用内部标准端口名（data / node_output） |
| `ui/core/node/composite_node.py` | `set_input_routing` / `set_output_routing` 入口规范化到标准名 + 清理别名脏键；`clear_input_routing` / `clear_output_routing` 别名宽松匹配；expand/collapse 流程先 `RouteCache.flush` 再断言；断言失败不 rollback（仅 ERROR 日志） |
| `ui/canvas/mixins/canvas_edge_render_gate.py` | `CANONICAL_SCAN_INTERVAL_MS` 3_000 → 10_000；`_run_scan` 引入 noisy 判定 + summary/set dump 分级日志 |
| `ui/core/state/`（15 模块 + 7 测试）+ 6 处业务接入（node_process / composite_node / canvas_view / canvas_layout / canvas_edge_render_gate） | 状态机系统盘点：节点线 Phase 1-3 生产可用、Phase 2 中期接入；边线条 Phase 4 定义完成/单测绿但业务尚未接入 edge_item.py / canvas_view.py |
| `ui/canvas/mixins/canvas_selection.py` | `on_node_selected` 清除旧选中双写 `_is_custom_selected=False + setSelected(False)` 并 `scene.clearSelection()` 兜底；新选中同步 `setSelected(True)`；`_toggle_node_selection` 切换时双源判定双写 |
| `ui/canvas/canvas_view.py` | `SelectedNodesList.append/remove/clear` 三个写操作 API 同步 `setSelected()` |
| `ui/canvas/mixins/canvas_box_select.py` | `clear_box_selection` 清除框选时同步 `_is_custom_selected=False + update()` 刷新 |
| `ui/canvas/items/composite_node_item.py` | 新增 `mousePressEvent`（单选 / Ctrl+多选 / 右键菜单 / 连线锚点命中四语义完整）；新增 `mouseDoubleClickEvent`（调用 `canvas.open_node_config(comp_id)` 打开配置面板，异常捕获 + 成败日志） |


---

**最后更新**：2026-07-15

# 2026-07-12 更新总览

[返回总索引](../README.md)

---

## 更新目录

- [01 _port_routing 端口路由机制](#01-_port_routing-端口路由机制)
- [02 代码规范统一化整改](#02-代码规范统一化整改)
- [03 节点资源限制组件](#03-节点资源限制组件)
- [04 复合节点连线与折叠修复](#04-复合节点连线与折叠修复)
- [05 单入口 DAG 防错机制](#05-单入口-dag-防错机制)
- [06 防错机制国际化](#06-防错机制国际化)
- [07 复合节点UI交互与连线系统第二轮修复](#07-复合节点ui交互与连线系统第二轮修复)
- [08 复合节点监控与日志修复](#08-复合节点监控与日志修复)
- [09 复合节点健壮性增强](#09-复合节点健壮性增强)
- [10 BNOS Build 驱动引擎方案](#10-bnos-build-驱动引擎方案)
- [11 except Exception pass 全面治理](#11-except-exception-pass-全面治理)
- [12 连线正交吸附功能](#12-连线正交吸附功能)
- [13 复合节点防错窗口风格统一](#13-复合节点防错窗口风格统一)
- [14 节点配置对话框国际化](#14-节点配置对话框国际化)

---

## 01 _port_routing 端口路由机制

### 问题背景

复合节点连线时，`_update_composite_config_edge` 将 `listen_upper_file` 写入内部节点 `config.json`，导致 `_identify_ports`（第 175 行 `if not listen`）检测到非空即跳过该节点，不再识别为输入端口——输入端口消失。

### 解决方案

将路由信息从内部节点 `config.json` 迁移到 `node_clusters.json` 中新增的 `_port_routing` 字段，实现端口路由与节点自身配置的解耦。

### 修改文件

| 文件 | 改动内容 |
|------|---------|
| `ui/core/node/composite_node.py` | 新增 `_port_routing` 辅助方法：`set_input_routing`、`set_output_routing`、`clear_input_routing`、`clear_output_routing`；`_sync_configs_for_expand` 双阶段同步（扫描画布连线 + 读取 `_port_routing`）；`_sync_configs_for_collapse` 双阶段同步（写回 `_port_routing` + 清除内部 config） |
| `ui/canvas/mixins/canvas_connections.py` | `_update_composite_config_edge` 三个分支全部改用 `set_input_routing` / `set_output_routing`，不再写入内部节点 `listen_upper_file`；`remove_edge` 复合→复合分支改用 `clear_input_routing` / `clear_output_routing`；删除不再使用的 `_sync_internal_out_connections` 方法 |
| `ui/core/node/composite_orchestrator.py` | 生成的编排器脚本在 `__main__` 中读取 `_port_routing.input`，注入 `external_input` 到 `runner.run()` |

### _port_routing 数据结构

```json
{
  "input": {
    "port_name": {"source_output_path": "nodes/xxx/output.json"}
  },
  "output": {
    "port_name": {
      "target_composite": "composite_xxx",
      "target_node": "internal_name",
      "target_port": "port_name"
    }
  }
}
```

### 约束范围

- **节点 `main.py`**：零改动。`_port_routing` 仅由编排器脚本读取注入，节点自身 `process()` 保持不变。
- **节点开发规范**：无新增约束，`main.py` 在复合模式下仍被 `importlib` 直接调用，不经过 `listener.py`。

---

## 03 节点资源限制组件

详见 [03_节点资源限制组件.md](./03_节点资源限制组件.md)。

### 摘要

- **全平台资源限制**：Linux cgroups v2（CPU + 内存硬限制）、Windows Job Objects（CPU + 内存硬限制）、macOS（nice 优先级）
- **config.json 字段**：`priority` / `cpu_affinity` / `cpu_percent` / `memory_mb`，均为可选
- **22 个新测试**：工厂函数、优先级映射、上下文管理器、优雅降级、macOS 回退、配置边界
- **文档更新**：`config_json_开发规范` 新增第八章，7 种场景推荐配置

---

## 04 复合节点连线与折叠修复

### 展开/折叠连线更新修复

- `_morph_composite_to_internal_edges`：创建临时连线后补充 `update_path()` 调用
- `_expand_composite`：恢复内部连线后补充 `update_path()` 调用
- `_morph_internal_to_composite_edges`：恢复原始连线后补充 `update_path()` 调用

### 展开/折叠抖动修复

- `_sync_composite_group_movement`：跳过拖拽中的节点，避免 Qt 已定位后重复 `setPos` 触发双重 `itemChange`
- 新增 `_batch_updating` 标志：展开/折叠时包裹逐节点刷新，循环结束后调用 `_batch_update_edges_for_nodes` 一次性刷新所有连线

### config.json 写入诊断修复

- `_update_composite_config_edge` 多处静默 `return` 增加详细日志
- 增加 `_composite_manager` 懒初始化保底

### _port_routing 残留清理

- `_refresh_ports_on_collapse` 末尾新增清理逻辑：遍历 `_port_routing` 删除引用已失效端口名的条目

---

## 05 单入口 DAG 防错机制

### 核心约束

复合节点必须为单入口 DAG。支持的拓扑结构：`A→B→C` 或 `A→B` 同时 `A→C`，不允许 `A→C` 且 `B→C`。

### 新增方法

`_validate_dag_single_entry` — 统计 `in_degree==0` 且 `listen_upper_file` 为空的候选入口节点数：

| 候选数 | 行为 |
|--------|------|
| 0 | 拒绝 — 提示"未检测到入口节点" |
| 1 | 通过 |
| 2+ | 拒绝 — 提示"必须且仅有一个入口" |

### 触发位置

| 操作 | 时机 | 拒绝行为 |
|------|------|---------|
| 压缩 | `compress()` 端口识别后 | `return False, err_msg, None` |
| 折叠 | `_collapse_composite()` 状态变更前 | `QMessageBox.warning` + `return`，展开态保持不变 |

---

## 06 防错机制国际化

新增 3 个翻译键，覆盖中英文：

| 键名 | 中文 | English |
|------|------|---------|
| `_COMPOSITE_NO_ENTRY` | "未检测到入口节点" | "No entry node detected" |
| `_COMPOSITE_MULTI_ENTRY` | "检测到 {count} 个入口节点" | "Detected {count} entry nodes" |
| `COMPOSITE_COLLAPSE_BLOCKED_TITLE` | "无法折叠" | "Cannot Collapse" |

修改文件：
- `ui/core/i18n/translation_keys.py` — 新增键定义
- `ui/core/i18n/strings_cn.json` — 中文翻译
- `ui/core/i18n/strings_en.json` — 英文翻译

---

## 07 复合节点UI交互与连线系统第二轮修复

### 右键菜单展开/折叠

- `canvas_menus.py`：`_show_composite_node_menu` 新增「展开」/「折叠」菜单项，替代双击展开
- 解决 canvas 级 `contextMenuEvent` 拦截 CompositeNodeItem 事件导致右键菜单缺失问题

### 复合节点输出锚点连线

- `composite_node_item.py`：新增 `output_anchor` / `input_anchor` / `node_name` 属性，使连线系统能识别复合节点锚点
- `canvas_connections.py`：`create_edge` 处理复合节点涉及的连线，通过 `_update_composite_config_edge` 双向写入 `out_connections`
- `remove_edge`：新增 `_clean_target_config` / `_clean_source_out_connections` 帮助方法，处理复合节点目标的 config 清理

### 展开态UI交互修复

- `composite_group_frame.py`：重写 `shape()` 方法，仅覆盖折叠按钮区域，避免默认矩形响应区拦截内部节点和锚点的鼠标事件

### 折叠/展开线条残留清理

- `compress()` / `decompress()`：压缩时隐藏内部连线并记录到 `_internal_edges`，解耦时恢复
- `_handle_line_visibility_on_collapse/expand`：多复合节点场景安全性——检查连线端点是否属于其他已展开的复合节点，避免误恢复

### 复合节点连线 config.json 同步

- 每次展开/折叠均重新对齐 `config.json`：
  - `_sync_configs_for_expand`：展开时扫描画布连线 + 读取 `_port_routing`，写入内部节点 `listen_upper_file` 和 `out_connections`
  - `_sync_configs_for_collapse`：折叠时从内部节点读取，写回 `_port_routing` 并清除内部 config
- 端口识别 `_identify_ports`：已从纯 DAG 边检测改为同时检查 `config.json` 的 `listen_upper_file` 和 `out_connections`

### 折叠后锚点失效修复

- `_refresh_ports_on_collapse`：`update_ports()` 会销毁旧锚点，原有边仍持有旧锚点引用→失效
- 修复方案：保存复合节点相关边→刷新端口→重新绑定边到新锚点（通过 `find_anchor_by_port`），绑定失败的过时边删除

### 内部节点拖动抖动修复

- `canvas_event_handlers.py`：新增 `_prepare_composite_drag_anchor`（mousePressEvent 预设锚点）和 `_clear_composite_drag_anchors`
- `_sync_composite_group_movement` 重写：每帧更新锚点位置，仅实际拖拽节点存在偏移，消除非拖拽节点被误判为"移动"导致的反馈回路抖动
- 关联框 `composite_group_frame.py` 同步跟随

### 文件保存 PermissionError 重试

- `composite_node.py` 的 `save()` 方法：新增 `_saving` 可重入锁 + 3 次重试（间隔 0.1s→0.2s→0.3s）+ 删除后重命名兜底，解决 Windows 文件锁冲突

### 其他修复

- `SelectedNodesList` 非 JSON 可序列化：`compress()` 中 `node_names = list(node_names)` 标准化为普通列表
- `AnchorItem.__init__()` 参数不匹配：修正构造参数为实际签名 `(x, y, anchor_type, port_name, port_type, size, parent)`

---

## 修改文件清单

| 文件 | 类型 |
|------|------|
| `ui/core/node/composite_node.py` | 修改 |
| `ui/canvas/mixins/canvas_connections.py` | 修改 |
| `ui/core/node/composite_orchestrator.py` | 修改 |
| `ui/core/i18n/translation_keys.py` | 修改 |
| `ui/core/i18n/strings_cn.json` | 修改 |
| `ui/core/i18n/strings_en.json` | 修改 |
| `ui/canvas/items/composite_node_item.py` | 修改 |
| `ui/canvas/items/composite_group_frame.py` | 修改 |
| `ui/canvas/mixins/canvas_menus.py` | 修改 |
| `ui/canvas/mixins/canvas_event_handlers.py` | 修改 |
| `docs/design/复合节点开发方案.md` | 更新 |

---

## 08 复合节点监控与日志修复

详见 [04_复合节点监控与日志修复.md](./04_复合节点监控与日志修复.md)。

### 摘要

- **监控黑洞修复**：`CompositeNodeItem` 集成 `NodeStatusWidget`，折叠态显示聚合 CPU/MEM/状态灯
- **日志黑洞修复**：`stdout/stderr=PIPE` → 文件落盘（`composite_output.log` / `composite_error.log`）；View Log 支持复合双日志
- **PID 回退**：`get_node_pid()` 新增 `__composite_{id}.pid` 查找路径

---

## 09 复合节点健壮性增强

详见 [05_复合节点健壮性增强.md](./05_复合节点健壮性增强.md)。

### 摘要

- **拖拽性能（P0）**：移除 per-frame anchor 写回，`mouseRelease` 批量持久化
- **磁盘异常（P0）**：3 处 `PermissionError`/`OSError` try/except + themed_message 弹窗
- **config 冲突（P1）**：展开时快照 → 折叠时对比 → 日志警告
- **断点续跑（P1）**：`_try_read_cache()` 检查 `output.json` 跳过已完成节点
- **分布式接口（P2）**：`TransportHandler` ABC 预埋

---

## 10 BNOS Build 驱动引擎方案

详见 [06_BNOS_Build_驱动引擎方案.md](./06_BNOS_Build_驱动引擎方案.md)。

### 摘要

- **概念升级**：导出模式 → 驱动层注入；引擎与源文件完全隔离
- **命令**：`bnos build` / `--force` / `--clean` / `--update` / `--docker`
- **运行时**：`python -m bnos_runtime.engine pipeline.json`（无需 BNOS GUI）

---

## 11 except Exception: pass 全面治理

详见 [07_except_Exception_pass_全面治理.md](./07_except_Exception_pass_全面治理.md)。

### 摘要

- **规模**：100 处 → 0 处，26 文件修改
- **类型**：`OSError`、`ProcessLookupError`、`NoSuchProcess`/`AccessDenied`、`RuntimeError`、`ValueError`
- **原则**："只捕获真正可能发生的异常"

---

## 12 连线正交吸附功能

详见 [08_连线正交吸附功能.md](./08_连线正交吸附功能.md)。

### 摘要

- **功能**：拖拽折叠点吸附 90°/180° 直角交点
- **交互**：Shift 临时禁用；右键菜单开关；`SNAP_THRESHOLD = 20px`

---

## 13 复合节点防错窗口风格统一

详见 [09_复合节点防错窗口风格统一.md](./09_复合节点防错窗口风格统一.md)。

### 摘要

- **6 处 QMessageBox** → `themed_message()`，深色圆角无边框与 BNOS 主题一致

---

## 14 节点配置对话框国际化

详见 [10_节点配置对话框国际化.md](./10_节点配置对话框国际化.md)。

### 摘要

- **20 处硬编码字符串** → `t(TK.KEY)`；Resource Limits 区域全面国际化；+19 键

---

**最后更新**：2026-07-12

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
- [15 复合节点配置文件与资源组](#15-复合节点配置文件与资源组)
- [16 启动守卫与资源监测双层架构](#16-启动守卫与资源监测双层架构)

---

## 01 _port_routing 端口路由机制

详见 [01__port_routing端口路由机制.md](./01__port_routing端口路由机制.md)。

---

## 02 代码规范统一化整改

详见 [02_代码规范统一化整改.md](./02_代码规范统一化整改.md)。

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

详见 [04_复合节点连线与折叠修复.md](./04_复合节点连线与折叠修复.md)。

---

## 05 单入口 DAG 防错机制

详见 [05_单入口DAG防错机制.md](./05_单入口DAG防错机制.md)。

---

## 06 防错机制国际化

详见 [06_防错机制国际化.md](./06_防错机制国际化.md)。

---

## 07 复合节点UI交互与连线系统第二轮修复

详见 [07_复合节点UI交互与连线系统第二轮修复.md](./07_复合节点UI交互与连线系统第二轮修复.md)。

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

详见 [08_复合节点监控与日志修复.md](./08_复合节点监控与日志修复.md)。

### 摘要

- **监控黑洞修复**：`CompositeNodeItem` 集成 `NodeStatusWidget`，折叠态显示聚合 CPU/MEM/状态灯
- **日志黑洞修复**：`stdout/stderr=PIPE` → 文件落盘（`composite_output.log` / `composite_error.log`）；View Log 支持复合双日志
- **PID 回退**：`get_node_pid()` 新增 `__composite_{id}.pid` 查找路径

---

## 09 复合节点健壮性增强

详见 [09_复合节点健壮性增强.md](./09_复合节点健壮性增强.md)。

### 摘要

- **拖拽性能（P0）**：移除 per-frame anchor 写回，`mouseRelease` 批量持久化
- **磁盘异常（P0）**：3 处 `PermissionError`/`OSError` try/except + themed_message 弹窗
- **config 冲突（P1）**：展开时快照 → 折叠时对比 → 日志警告
- **断点续跑（P1）**：`_try_read_cache()` 检查 `output.json` 跳过已完成节点
- **分布式接口（P2）**：`TransportHandler` ABC 预埋

---

## 10 BNOS Build 驱动引擎方案

详见 [10_BNOS_Build_驱动引擎方案.md](./10_BNOS_Build_驱动引擎方案.md)。

### 摘要

- **概念升级**：导出模式 → 驱动层注入；引擎与源文件完全隔离
- **命令**：`bnos build` / `--force` / `--clean` / `--update` / `--docker`
- **运行时**：`python -m bnos_runtime.engine pipeline.json`（无需 BNOS GUI）

---

## 11 except Exception: pass 全面治理

详见 [11_except_Exception_pass_全面治理.md](./11_except_Exception_pass_全面治理.md)。

### 摘要

- **规模**：100 处 → 0 处，26 文件修改
- **类型**：`OSError`、`ProcessLookupError`、`NoSuchProcess`/`AccessDenied`、`RuntimeError`、`ValueError`
- **原则**："只捕获真正可能发生的异常"

---

## 12 连线正交吸附功能

详见 [12_连线正交吸附功能.md](./12_连线正交吸附功能.md)。

### 摘要

- **功能**：拖拽折叠点吸附 90°/180° 直角交点
- **交互**：Shift 临时禁用；右键菜单开关；`SNAP_THRESHOLD = 20px`

---

## 13 复合节点防错窗口风格统一

详见 [13_复合节点防错窗口风格统一.md](./13_复合节点防错窗口风格统一.md)。

### 摘要

- **6 处 QMessageBox** → `themed_message()`，深色圆角无边框与 BNOS 主题一致

---

## 14 节点配置对话框国际化

详见 [14_节点配置对话框国际化.md](./14_节点配置对话框国际化.md)。

### 摘要

- **20 处硬编码字符串** → `t(TK.KEY)`；Resource Limits 区域全面国际化；+19 键

---

## 15 复合节点配置文件与资源组

详见 [15_复合节点配置文件与资源组.md](./15_复合节点配置文件与资源组.md)。

### 摘要

- **composite.json** Schema 定义（身份 + DAG + 端口 + 资源预算），损坏时从 node_clusters.json 自愈恢复
- **node_registry.json** 运行时登记簿（子节点状态、PID、启动来源、独立运行次数）
- **压缩时**创建 `composite_nodes/<id>/` 完整目录结构（配置 + 注册表 + 日志目录）
- **启动时**自动迁移已有复合节点（补全缺失的 composite.json）
- **解压缩时**日志存档到 `.archive/<id>_<fingerprint>_<timestamp>/`，删除整个配置目录
- **日志路径**从 `{name}_venv/logs/` 迁移到 `composite_nodes/<id>/logs/`，不再依赖 display_name
- 复合节点 venv 绑定生命周期：解压缩 = 删除

### 修改文件

| 文件 | 改动 |
|------|------|
| `ui/core/node/composite_node.py` | +280 行（10 个新方法） |
| `ui/panels/node_list_ops.py` | _get_log_files 路径修复 |

---

## 16 启动守卫与资源监测双层架构

详见 [16_启动守卫与资源监测双层架构.md](./16_启动守卫与资源监测双层架构.md)。

### 摘要

- **启动守卫（双向互斥）**：独立节点启动 → 检查所属复合节点是否运行中（三选一弹窗）；复合节点启动 → 检查子节点是否独立运行中（自动停止后启动）
- **资源监测双层**：复合节点 orchestrator 进程独立监测行（含 PID + CPU + 内存）；子节点 `[sub]` 缩进行
- **运行中**：子节点在 orchestrator 进程内，显示 `—` 资源（不重复计算）
- **停止中**：子节点如独立运行则显示各自 PID 资源

### 修改文件

| 文件 | 改动 |
|------|------|
| `ui/core/node/composite_node.py` | +3 方法（check_subnode_start / check_composite_start / stop_conflicting_subnodes） |
| `ui/main_window/node.py` | start_selected_node_by_name 守卫检查 |
| `ui/panels/resource_monitor.py` | _update_node_stats + _refresh_node_table 重写 |
| `ui/panels/resource_monitor_dock.py` | 同上 |
| `ui/panels/_shared/system_resource_collector.py` | +3 方法（get_composite_pid / collect_group_stats / _format_memory） |
| `ui/core/i18n/translation_keys.py` + strings | +2 键 |

---

**最后更新**：2026-07-12

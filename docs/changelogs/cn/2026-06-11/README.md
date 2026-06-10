# 2026-06-11 更新日志

## 📋 更新概述

本次更新解决了 **`canvas_layout.json` 被错误改写**的核心问题。当连线绑定到特定端口锚点（`prompt`、`context` 等）后，项目重启打开画布时，连线会错误降级到默认锚点，导致保存时 `target_port` 从 `"prompt"` 变为 `"default"`，并可能产生重复连线。本次修复引入「**期望端口名记忆机制**」和「**锚点缺失不降级保护**」，确保连线与正确的锚点始终绑定，配置文件不再被静默改写。

---

## ✨ 更新内容

### 1. 🔌 连线端口锚点绑定保护

**核心修复**：
- `EdgeItem` 新增 `_desired_target_port_name` / `_desired_source_port_name` 字段，记住连线期望绑定的端口名
- `_setup_anchor_binding` 中：指定端口但找不到锚点时，**不 fallback 到默认锚点**，保持 `end_anchor = None`
- `_validate_edge_anchor_binding` 中：优先使用「期望端口名」查找锚点，而非「当前锚点的 port_name」（后者可能已错绑到 default）
- `load_layout` 中：JSON 中指定了非 default 端口但找不到对应锚点时，**跳过该连线并发出警告**，不降级创建

**关键保护机制**：
- **不降级（No Silent Fallback）**：指定了特定端口就必须绑定到该端口的锚点，找不到就跳过
- **记忆优先（Desired > Current）**：锚点重建时以"期望端口名"而非"当前锚点名"为依据
- **警告可见（Verbose Warning）**：所有异常绑定通过 `logger.warning` 输出到日志

**修改文件**（3 个文件）：
- `ui/canvas/items/edge_item.py`（构造函数新增参数、`_setup_anchor_binding` 增强）
- `ui/canvas/canvas_layout.py`（`load_layout` 锚点缺失跳过、`_validate_edge_anchor_binding` 期望端口优先查找）
- `ui/canvas/canvas_connections.py`（`create_edge` 调用传递端口名参数）

**详细文档**：[连线端口锚点绑定保护与 canvas_layout 防改写](./01_连线端口锚点绑定保护与canvas_layout防改写.md)

---

## 🎯 问题根因总结

| 编号 | 问题 | 影响 |
|------|------|------|
| 1 | `load_layout` 被调用两次 | 第二次调用时锚点已重建，edges 集合被重复添加 |
| 2 | `EdgeItem` 不记忆期望端口名 | 锚点重建后校验逻辑用 `end_anchor.port_name` 查找，而它已经是 `"default"` |
| 3 | 指定端口锚点缺失时 fallback 到默认锚点 | `get_input("prompt")` 返回 `None` 时，`EdgeItem` 被动绑定到默认锚点，保存时 port 信息不可逆丢失 |

---

## 🧪 验证场景

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 指定端口 `prompt` 存在 | ✅ 正常绑定 | ✅ 正常绑定 |
| 指定端口 `prompt` 不存在（config 缺少 `source: "node"`） | ❌ 降级绑定 default，保存时 port 丢失 | ✅ 跳过并警告，文件不被改写 |
| 样式切换后锚点重建 | ❌ 重新绑定可能错到 default | ✅ 使用期望端口名重找正确锚点 |
| 同一对节点多端口连线（prompt + default） | ❌ 可能合并为 default | ✅ 保持各自端口绑定 |

---

## 📋 总览

| 功能 | 状态 |
|------|------|
| EdgeItem 期望端口名记忆字段 | ✅ 完成 |
| 指定端口但找不到锚点时跳过（不降级） | ✅ 完成 |
| _validate_edge_anchor_binding 期望端口优先查找 | ✅ 完成 |
| 手动连线时传递端口名参数 | ✅ 完成 |
| canvas_layout.json 不再被错误改写 | ✅ 完成 |
| 重复连线创建防护 | ✅ 完成 |

---

**更新日期**：2026-06-11

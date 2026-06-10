# 连线端口锚点绑定保护与 canvas_layout 防改写

## 📋 更新概述

本次更新解决了**项目启动后打开画布时 `canvas_layout.json` 被错误改写**的核心问题。当连线绑定到特定端口锚点（如 `prompt`、`context`）时，锚点重建后连线会错误 fallback 到默认锚点，导致保存时 `target_port` 从 `"prompt"` 变为 `"default"`，并可能产生重复连线。本次修复引入「期望端口名记忆」机制和「锚点缺失不降级」保护，确保连线与正确的锚点始终绑定。

---

## 🎯 问题根因分析

### 问题现象

1. 用户创建项目，在画布上连接连线到 `prompt` 端口
2. `canvas_layout.json` 正确保存了 `"target_port": "prompt"`
3. 重启应用后打开项目 → `canvas_layout.json` 被改写：
   - `"target_port": "prompt"` → `"target_port": "default"`
   - 出现重复连线条目

### 三重根因

| 编号 | 问题 | 影响 |
|------|------|------|
| 1 | `load_layout` 被调用两次 | 第二次调用时锚点已重建，edges 集合被重复添加 |
| 2 | `EdgeItem` 不记忆期望的端口名 | 锚点重建后 `_validate_edge_anchor_binding` 用 `end_anchor.port_name` 查找，而它已经是 `"default"` |
| 3 | 指定端口锚点缺失时 fallback 到默认锚点 | `get_input("prompt")` 返回 `None` 时，`EdgeItem` 被动绑定到 `input_anchor`（默认锚点），保存时 port 信息不可逆丢失 |

---

## 🔧 核心变更

### 1. EdgeItem：期望端口名记忆字段

**新增字段**（2 个）：
- `_desired_target_port_name`：目标端口名（"prompt" / "context" / None）
- `_desired_source_port_name`：源端口名

**构造函数签名**：
```python
def __init__(self, start_node, end_node, canvas=None,
             target_anchor=None, source_anchor=None,
             target_port_name=None, source_port_name=None):
```

**_setup_anchor_binding 新增逻辑**：
- 如果 `_desired_target_port_name` 已设置，优先从 `anchor_manager.get_input(port_name)` 查找
- 只有在**未指定特定端口名**时，才允许 fallback 到默认锚点
- 指定了端口名但找不到对应锚点时，保持 `end_anchor = None`，不降级绑定

**修改文件**：`ui/canvas/items/edge_item.py`

### 2. load_layout：端口锚点缺失跳过连线（不降级）

**新增保护逻辑**：在创建连线前验证锚点是否存在

```python
src_port = ed.get("source_port")
tgt_port = ed.get("target_port")

# 关键保护：指定了非 default 端口但找不到锚点 → 跳过 + 警告
if tgt_port and tgt_port != "default" and tgt_anchor is None:
    logger.warning("[load_layout] 跳过连线: 目标节点 '%s' 上找不到端口 '%s' 的锚点",
                   node_name, tgt_port)
    continue
```

**修改文件**：`ui/canvas/canvas_layout.py`

### 3. _validate_edge_anchor_binding：优先使用期望端口名

**查找顺序变更**：

```
查找锚点的顺序（修复后）：
  1. edge._desired_target_port_name  → 原始 JSON 中的 target_port
  2. edge.end_anchor.port_name       → 当前绑定的锚点名（可能已错）
  3. 无特定端口名 → 使用默认锚点
```

**不降级规则**：如果期望端口名是特定端口（非 default / None），找不到时保持 `end_anchor = None`，不 fallback。

**修改文件**：`ui/canvas/canvas_layout.py`

### 4. canvas_connections：手动创建连线时传递端口名

`create_edge()` 调用 `EdgeItem` 时也传递端口名参数，确保手动连线也具备锚点重建后的重新绑定能力。

```python
tgt_port_name = target_anchor.port_name if target_anchor else None
src_port_name = source_anchor.port_name if source_anchor else None
edge = EdgeItem(source_node, target_node, canvas,
                target_anchor, source_anchor,
                target_port_name=tgt_port_name,
                source_port_name=src_port_name)
```

**修改文件**：`ui/canvas/canvas_connections.py`

---

## 📝 修改文件清单

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| `ui/canvas/items/edge_item.py` | 修改 | 新增期望端口名字段，setup 绑定逻辑增强 |
| `ui/canvas/canvas_layout.py` | 修改 | load_layout 锚点缺失跳过 + _validate 期望端口优先查找 |
| `ui/canvas/canvas_connections.py` | 修改 | create_edge 调用时传递端口名参数 |

---

## 🧪 验证场景

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| 指定端口 `prompt` 存在 | ✅ 正常绑定 | ✅ 正常绑定 |
| 指定端口 `prompt` 不存在（config 缺少 `source: "node"`） | ❌ 降级绑定 default，保存时 port 丢失 | ✅ 跳过并警告，文件不被改写 |
| 样式切换后锚点重建 | ❌ 重新绑定可能错到 default | ✅ 使用期望端口名重找正确锚点 |
| 同一对节点多端口连线（prompt + default） | ❌ 可能合并为 default | ✅ 保持各自端口绑定 |

---

## 🔒 设计原则

1. **不降级（No Silent Fallback）**：指定了特定端口就必须绑定到该端口的锚点，找不到就跳过
2. **记忆优先（Desired > Current）**：锚点重建时以"期望端口名"而非"当前锚点名"为依据
3. **警告可见（Verbose Warning）**：所有异常绑定通过 `logger.warning` 输出到日志，便于排查

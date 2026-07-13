# 复合节点折叠 DAG 拓扑更新修复

[返回更新总览](./README.md)

---

## 背景

展开复合节点后重新编排子节点连接顺序（如将 A→B 改为 B→A），折叠后启动复合节点，数据处理结果未发生变化。例如：

- 原 DAG：node_4(data=1) → node_3(×3) → node_2(+1) → 结果 = 4
- 改为：node_4(data=1) → node_2(+1) → node_3(×3) → 预期结果 = 6

但实际结果仍为 4，说明新拓扑未生效。

---

## 根因分析

问题出在 `_collapse_composite` 方法的写入链路：

1. 折叠时 `internal_edge_info` 正确捕获了新连线（`src → node_2, tgt → node_3`）
2. 但只写入了内存字典 `comp["_internal_edges"]`
3. **`composite.json` 的 `edges` 字段从未更新**，仍保留首次压缩时的旧拓扑
4. `_sync_pipeline` 读取的是 `composite.json` → `pipeline.json` 使用旧 DAG
5. orchestrator.py 从 `pipeline.json` 读取拓扑 → 旧拓扑执行

此外，`_sync_pipeline` 仅在 `new_rules`（入口过滤规则变化）为真时才调用，即使 DAG 变了但过滤规则未变也不会触发更新。

### 关键代码路径（修复前）

```python
# 折叠时仅写入内存
comp["_internal_edges"] = internal_edge_info

# ... 其他操作 ...

# _sync_pipeline 仅当过滤规则变化时调用
new_rules = self._extract_entry_filter_rules(...)
if new_rules:                           # ← 条件限制
    comp_cfg = self._load_composite_config(comp_id)
    if comp_cfg:
        comp_cfg["input_filter_rules"] = new_rules
        self._write_composite_config(comp_id, comp_cfg)
        self._sync_pipeline(comp_id)    # ← 不会执行
```

---

## 修复方案

#### 文件：`ui/core/node/composite_node.py`

**1. 折叠时立即同步 edges 到 composite.json**

在 `comp["_internal_edges"] = internal_edge_info` 之后，立即加载 `composite.json` 并更新 `edges` 字段：

```python
comp["_internal_edges"] = internal_edge_info

# 同步 DAG 拓扑到 composite.json
comp_cfg = self._load_composite_config(comp_id)
if comp_cfg:
    comp_cfg["edges"] = [
        {"from": e["src"], "to": e["tgt"],
         "source_port": e.get("src_port", ""),
         "target_port": e.get("tgt_port", "")}
        for e in internal_edge_info
    ]
```

格式映射：`src→from, tgt→to, src_port→source_port, tgt_port→target_port`

**2. _sync_pipeline 改为无条件执行**

将 `_sync_pipeline` 从 `if new_rules:` 块内移到外面：

```python
new_rules = self._extract_entry_filter_rules(node_names, edges_list, nodes_data)
if new_rules and comp_cfg:
    comp["input_filter_rules"] = new_rules
    comp_cfg["input_filter_rules"] = new_rules

# 始终写入 composite.json 并同步 pipeline.json
# 即使过滤规则未变，DAG 拓扑（edges）也可能已变化
if comp_cfg:
    self._write_composite_config(comp_id, comp_cfg)
    self._sync_pipeline(comp_id)
    self._touch_pipe_signal(comp_id)
```

3. 同时写入 `.pipe` 信号文件，通知运行中的编排器热加载新 pipeline（如果编排器正在运行）。

---

## 修复后的完整链路

```
展开 → 用户重新连线 → 折叠
  ↓
_collapse_composite:
  1. internal_edge_info = [新的 edges]
  2. comp["_internal_edges"] = internal_edge_info        ← 内存
  3. comp_cfg["edges"] = 格式转换后的 edges              ← composite.json
  4. _write_composite_config(comp_id, comp_cfg)          ← 持久化
  5. _sync_pipeline(comp_id)                              ← pipeline.json
  6. _touch_pipe_signal(comp_id)                          ← .pipe 信号
  ↓
orchestrator.py:
  - 检测 .pipe → 重新加载 pipeline.json → 新拓扑生效
  - 或下次启动时读取最新 pipeline.json
```

---

## 修改文件清单

| 文件 | 改动 |
|------|------|
| `ui/core/node/composite_node.py` | `_collapse_composite` 新增 edges 同步到 composite.json；`_sync_pipeline` 改为无条件调用 |

---

**最后更新**：2026-07-13

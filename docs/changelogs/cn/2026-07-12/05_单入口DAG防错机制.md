# 单入口 DAG 防错机制

[返回更新总览](./README.md)

---

## 核心约束

复合节点必须为单入口 DAG。支持的拓扑结构：`A→B→C` 或 `A→B` 同时 `A→C`，不允许 `A→C` 且 `B→C`。

## 新增方法

`_validate_dag_single_entry` — 统计 `in_degree==0` 且 `listen_upper_file` 为空的候选入口节点数：

| 候选数 | 行为 |
|--------|------|
| 0 | 拒绝 — 提示"未检测到入口节点" |
| 1 | 通过 |
| 2+ | 拒绝 — 提示"必须且仅有一个入口" |

## 触发位置

| 操作 | 时机 | 拒绝行为 |
|------|------|---------|
| 压缩 | `compress()` 端口识别后 | `return False, err_msg, None` |
| 折叠 | `_collapse_composite()` 状态变更前 | `QMessageBox.warning` + `return`，展开态保持不变 |

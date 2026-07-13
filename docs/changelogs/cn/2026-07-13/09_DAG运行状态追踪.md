# 09 DAG 运行状态追踪

## 问题描述

复合节点 DAG 执行时无法追踪每个子节点的执行状态，不利于故障排查和监控。

## 修复方案

### 9.1 节点级状态追踪

**文件**：`ui/core/node/composite_orchestrator.py`

`DagRunner` 记录每个子节点的执行状态：
- `status`：ok / fail / pending
- `error`：错误信息
- `duration_ms`：执行耗时

**代码变更**：
```python
self._node_status = {}

# 在每个执行阶段记录状态
self._node_status[node_name] = {
    "status": "ok",
    "duration_ms": int((time.time() - t0) * 1000),
    "output_lines": len(output_text.splitlines())
}
```

### 9.2 状态持久化

**文件**：`ui/core/node/composite_orchestrator.py`

执行完成后写入 `status.json`，供 BNOS 监控。

**代码变更**：
```python
def _write_status(self):
    for node_name in self._node_paths:
        if node_name not in self._node_status:
            self._node_status[node_name] = {"status": "pending"}
    status = {
        "comp_id": "{comp_id}",
        "updated_at": datetime.now().isoformat(),
        "last_run_id": self._run_id,
        "nodes": self._node_status,
    }
    (COMP_DIR / "status.json").write_text(json.dumps(status, ...))
```

### 9.3 并行执行追踪

**文件**：`ui/core/node/composite_orchestrator.py`

并行节点的失败状态也会被记录。

## 修改文件清单

| 文件 | 改动 |
|------|------|
| `ui/core/node/composite_orchestrator.py` | 新增 `_node_status` 追踪；新增 `_write_status()` 方法 |

## 效果验证

修复后：
- ✅ 每个子节点的执行状态、错误信息、耗时都被记录
- ✅ 执行完成后状态持久化到 `status.json`
- ✅ 未执行的节点标记为 pending
- ✅ 并行节点的失败状态也会被记录

---

**最后更新**：2026-07-13

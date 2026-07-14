# 02 MUTEX-VIOLATION 互斥断言时序修复

## 错误表现

复合节点 expand / collapse 流程末尾抛出 `AssertionError: MUTEX-VIOLATION`，随后执行 `_rollback_cluster_state`：

```
AssertionError: MUTEX-VIOLATION expand ... node_clusters.json composite expanded=True 但磁盘 composite.json expanded=False (或反之)
```

## 根因 — 断言在 RouteCache.flush **之前**执行

expand/collapse 的 PhaseB/C 只写 `RouteCache` 内存缓存，真正把变更落到磁盘 JSON 是在 PhaseD `RouteCache.flush()`。但原来的互斥断言位置**紧接在 PhaseC 之后，flush 之前**：

```
❌ 旧时序：
  PhaseB CLEAR     → RouteCache 内存标记待清
  PhaseC CREATE    → RouteCache 内存标记待写
  ASSERT           → 从磁盘读 composite.json / listen_upper_file（仍是旧值！）
  FLUSH            → 才把 PhaseC 的新值真正写出去
  ROLLBACK(误报)   → 断言失败把一致的数据也回滚了
```

结果就是断言读到的是 **PhaseB CLEAR 之后、PhaseC FLUSH 之前**的瞬态磁盘值，出现「expanded 不一致」的假阳性，且 rollback 把**已经通过 RouteCache 正确编排的变更全部清空**。

## 修复 — FLUSH 放在 ASSERT 之前

```python
# ✅ 新时序：
PhaseB CLEAR → PhaseC CREATE → [PhaseD FLUSH 写盘] → ASSERT 读磁盘
```

核心代码：

```python
# 步骤 6：RouteCache.flush（原子写所有配置到磁盘）
# 必须放在互斥断言之前！否则断言读磁盘时还是旧值导致误报。
flushed = RouteCache.flush()
logger.info("[MORPH-EXPAND-SUMMARY] comp=%s PhaseD-FLUSH flushed_cfgs=%d", comp_id, flushed)

# 步骤 5.5：互斥硬断言（expand 后必须 expanded=True 一致）
# 断言失败不再 rollback：因为 flush 已经原子写盘，rollback 无法恢复磁盘数据
mutex_assertion_ok = True
try:
    self._assert_mutex_consistency(comp_id, morph_list, expanded=True)
except AssertionError as ae:
    mutex_assertion_ok = False
    logger.error(
        "[MORPH-MUTEX-FAILED-EXPAND] %s (RouteCache already flushed=%d, skip rollback)",
        ae, flushed, exc_info=True,
    )
```

collapse 流程做完全相同的调整。

### 附带修复 — 断言失败不 rollback

由于 flush 已经**原子持久化到磁盘**了，`_rollback_cluster_state` 只能回滚内存里的 `node_clusters.json` 对象，无法回滚磁盘，结果会是**内存 ↔ 磁盘更不一致**。所以断言失败只记录 ERROR，不再触发 rollback。

断言 4 项检查：
1. `node_clusters.json expanded` 与 `composite.json expanded` 布尔一致
2. 路由键数相等（expand：输入/输出路由数 = 子节点实际端口数）
3. `_assert_input_mutex_consistency`：子节点 `config.json listen_upper_file` = composite.json 记录的上游 output.json
4. `_assert_output_mutex_consistency`：子节点 `config.json output_file` = composite.json 记录的下游 listen 反查

## 验证点

1. expand 后：`mutex_assertion=True`，没有 `MUTEX-VIOLATION` ERROR
2. collapse 后：`mutex_assertion=True`，没有 `MUTEX-VIOLATION` ERROR
3. 连续 expand ↔ collapse 10 次，磁盘上 `composite.json expanded` 与内存值始终保持一致
4. 即使真的不一致（用户手动改坏配置），只 ERROR 日志，不会误回滚

## 修改文件

| 文件 | 改动 |
|------|------|
| `ui/core/node/composite_node.py` | `expand_composite` / `collapse_composite` 把 `RouteCache.flush()` 移动到 `_assert_mutex_consistency` 之前；断言失败从 `raise + rollback` 改为 `ERROR 日志记录 + 跳过 rollback（已写盘）` |

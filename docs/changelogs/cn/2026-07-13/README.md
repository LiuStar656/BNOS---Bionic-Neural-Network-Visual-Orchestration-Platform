# 2026-07-13 更新总览

[返回总索引](../README.md)

---

## 更新目录

- [01 复合节点右键菜单优化与输入锚点独占检测](#01-复合节点右键菜单优化与输入锚点独占检测)
- [02 复合节点折叠 DAG 拓扑更新修复](#02-复合节点折叠dag拓扑更新修复)

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

## 修改文件清单

| 文件 | 改动 |
|------|------|
| `ui/canvas/mixins/canvas_menus.py` | 重写 `_show_composite_node_menu`；新增 `_on_toggle_expand` |
| `ui/canvas/mixins/canvas_connections.py` | `create_edge` 新增输入锚点独占检测 |
| `ui/core/node/composite_node.py` | `_collapse_composite` 新增 DAG 拓扑同步逻辑 |

---

**最后更新**：2026-07-13

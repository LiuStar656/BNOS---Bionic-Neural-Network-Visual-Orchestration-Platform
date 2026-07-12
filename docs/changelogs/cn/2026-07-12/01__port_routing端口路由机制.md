# _port_routing 端口路由机制

[返回更新总览](./README.md)

---

## 问题背景

复合节点连线时，`_update_composite_config_edge` 将 `listen_upper_file` 写入内部节点 `config.json`，导致 `_identify_ports`（第 175 行 `if not listen`）检测到非空即跳过该节点，不再识别为输入端口——输入端口消失。

## 解决方案

将路由信息从内部节点 `config.json` 迁移到 `node_clusters.json` 中新增的 `_port_routing` 字段，实现端口路由与节点自身配置的解耦。

## 修改文件

| 文件 | 改动内容 |
|------|---------|
| `ui/core/node/composite_node.py` | 新增 `_port_routing` 辅助方法：`set_input_routing`、`set_output_routing`、`clear_input_routing`、`clear_output_routing`；`_sync_configs_for_expand` 双阶段同步（扫描画布连线 + 读取 `_port_routing`）；`_sync_configs_for_collapse` 双阶段同步（写回 `_port_routing` + 清除内部 config） |
| `ui/canvas/mixins/canvas_connections.py` | `_update_composite_config_edge` 三个分支全部改用 `set_input_routing` / `set_output_routing`，不再写入内部节点 `listen_upper_file`；`remove_edge` 复合→复合分支改用 `clear_input_routing` / `clear_output_routing`；删除不再使用的 `_sync_internal_out_connections` 方法 |
| `ui/core/node/composite_orchestrator.py` | 生成的编排器脚本在 `__main__` 中读取 `_port_routing.input`，注入 `external_input` 到 `runner.run()` |

## _port_routing 数据结构

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

## 约束范围

- **节点 `main.py`**：零改动。`_port_routing` 仅由编排器脚本读取注入，节点自身 `process()` 保持不变。
- **节点开发规范**：无新增约束，`main.py` 在复合模式下仍被 `importlib` 直接调用，不经过 `listener.py`。

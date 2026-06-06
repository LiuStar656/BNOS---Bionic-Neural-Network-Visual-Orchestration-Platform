# 🔧 异步启动/停止节点，不阻塞 GUI

## 🔧 异步启动/停止节点，不阻塞 GUI (2026-06-05)

### 问题描述

**启动/停止节点时 GUI 无响应**
- **问题**：启动或停止节点时，由于操作是同步阻塞的，导致整个 GUI 无响应
- **影响**：用户无法在节点启动/停止期间进行其他操作，体验不佳

### 修复方案

**异步启动/停止机制**

1. **单个节点操作异步化**
   - 立即更新 UI 状态（显示"启动中..."或"停止中..."）
   - 在后台异步执行启动/停止操作
   - 操作完成后更新最终状态

2. **批量操作逐个执行**
   - 一次操作提示"正在启动/停止 N 个节点..."
   - 每隔 100ms 启动/停止一个节点
   - 全部完成后显示汇总结果

### 技术实现

```python
def start_selected_node_by_name(self, node_name):
    """启动节点（异步执行）"""
    # 立即显示启动中状态
    self.node_list_panel.update_node_status(node_name, 'idle')
    self.show_toast("正在启动节点...", "info")
    
    # 异步执行启动
    QTimer.singleShot(10, lambda: self._start_node_async(node_name))

def _start_node_async(self, node_name):
    """异步启动节点（内部方法）"""
    success, err = start_node_process(node_info)
    
    # 在主线程中更新 UI
    def on_complete():
        if success:
            self.show_toast("节点已启动", "success")
        else:
            self.show_toast("启动失败: " + err, "error")
    
    QTimer.singleShot(10, on_complete)
```

### 修改的文件

- `ui/main_window.py` - 添加 `_start_node_async`, `_stop_node_async` 方法
- `ui/panels/node_list_panel.py` - 修改 `batch_start_nodes`, `batch_stop_nodes` 方法
- `ui/panels/node_list_dock.py` - 修改 `batch_start_nodes`, `batch_stop_nodes` 方法
- `ui/core/strings_cn.json` - 添加 "_k_node_starting", "_k_node_stopping" 翻译
- `ui/core/strings_en.json` - 添加 "_k_node_starting", "_k_node_stopping" 翻译

### 验收标准

✅ 启动节点时 GUI 可以正常响应操作
✅ 停止节点时 GUI 可以正常响应操作
✅ 批量启动/停止节点时 GUI 不阻塞
✅ 显示"正在启动..."、"正在停止..."等过渡状态提示

---